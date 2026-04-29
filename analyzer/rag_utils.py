import json
import logging
import base64
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

def rag_pipeline(text: str, query: str = "Summarize this research paper"):
    try:
        text = text or ""
        if len(text.strip()) < 20:
            return {"summary": "Not enough content in the document to analyze."}

        client = Groq(api_key=settings.GROQ_API_KEY)

        # ✅ EXTENDED CONTEXT LIMIT (Covers most full papers)
        MAX_CHARS = 30000
        context = text[:MAX_CHARS]

        prompt = f"""
You are an expert research assistant.

Analyze the research paper and provide:
- Summary
- Key Contributions
- Methodology
- Results
- Limitations

CONTEXT:
{context}
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert academic research assistant. Be concise."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
        )

        return {
            "summary": response.choices[0].message.content
        }

    except Exception as e:
        logger.error("GROQ Pipeline Error", exc_info=True)
        return {
            "summary": f"Error analyzing the paper: {str(e)}"
        }

def analyze_text_with_groq(text: str, prompt: str = "Summarize this:") -> dict:
    """
    Analyze research paper using Groq AI with fallback to ml_processor.
    Returns a dict with structured analysis keys — never a plain str.
    """
    word_count = len(text.split())
    unique_words = len(set(text.split()))
    
    _safe_dict = lambda summary: {
        "summary": summary, "abstract": "", "keywords": [], "methodology": [],
        "technologies": [], "goal": "", "impact": "", "publication_year": "",
        "authors": [], "research_gaps": [], "conclusion": "",
        "statistics": {"word_count": word_count, "unique_words": unique_words},
    }
    
    # Limit text to stay well within TPM limits:
    # llama-3.3-70b-versatile: ~12k TPM → cap at 8000 chars (~2000 tokens of text)
    # llama-3.1-8b-instant:    ~6k TPM  → cap at 5000 chars (~1250 tokens of text)
    TEXT_CAP_70B = 8000
    TEXT_CAP_8B  = 5000

    analysis_prompt_template = """Analyze the following research paper and return a JSON object with these keys:
- summary: executive summary (80-120 words)
- abstract: original or reconstructed abstract
- keywords: list of 8-15 technical keywords
- methodology: list of methods/algorithms used
- technologies: list of software/hardware mentioned
- goal: primary research objective
- impact: contributions and real-world applications
- research_gaps: list of 3-5 limitations or future work areas
- conclusion: summary of final findings
- datasets: list of datasets mentioned
- authors: list of author full names
- publication_year: 4-digit year string

TEXT:
{text}"""

    def _call_groq(model: str, text_cap: int):
        client = Groq(api_key=settings.GROQ_API_KEY)
        trimmed = text[:text_cap]
        full_prompt = analysis_prompt_template.format(text=trimmed)
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return only a valid JSON object, no markdown formatting."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3,
            max_tokens=1024,
        )

    def _parse_response(response) -> dict:
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()
        if content.endswith('```'):
            content = content[:-3].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}, content: {content[:200]}")
            return {
                "summary": content[:500] if content else "",
                "abstract": "", "keywords": [], "methodology": [],
                "technologies": [], "goal": "", "impact": "",
                "authors": [], "publication_year": "",
                "research_gaps": [], "conclusion": "", "datasets": []
            }

    try:
        # Try the large model first
        response = _call_groq("llama-3.3-70b-versatile", TEXT_CAP_70B)
        data = _parse_response(response)

    except Exception as e:
        err_str = str(e)
        # On rate limit / token limit, fall back to the fast small model
        if '413' in err_str or '429' in err_str or 'rate_limit' in err_str or 'too large' in err_str.lower():
            logger.warning(f"Groq 70b rate/size limit hit, falling back to 8b model: {err_str[:100]}")
            try:
                response = _call_groq("llama-3.1-8b-instant", TEXT_CAP_8B)
                data = _parse_response(response)
            except Exception as e2:
                logger.error(f"Groq 8b fallback also failed: {e2}", exc_info=True)
                return _safe_dict(f"Error analyzing with Groq: {str(e2)}")
        else:
            logger.error(f"Groq analysis error: {e}", exc_info=True)
            return _safe_dict(f"Error analyzing with Groq: {err_str}")

    # Add required stats and defaults
    data["statistics"] = {"word_count": word_count, "unique_words": unique_words}
    data.setdefault("research_gaps", [])
    data.setdefault("conclusion", "")
    data.setdefault("datasets", [])

    logger.info(f"Groq analysis completed - summary: {len(data.get('summary', ''))} chars, keywords: {len(data.get('keywords', []))}")
    return data

def analyze_image_with_groq(image_file) -> dict:
    """
    Analyze a research paper image using Groq Vision model.
    """
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Read and encode image
        image_file.seek(0)
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        prompt = """
        Analyze this research paper image and provide a comprehensive JSON extraction.
        Extract all text first, then provide:
        - summary: A clear executive summary of what this image shows.
        - content_text: The full text extracted from the image.
        - keywords: List of technical keywords.
        - goal: The primary objective mentioned.
        - authors: Any author names found.
        - publication_year: Year of publication if found.
        
        Return ONLY valid JSON.
        """
        
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean up JSON
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()
        if content.endswith('```'):
            content = content[:-3].strip()
            
        try:
            data = json.loads(content)
        except:
            data = {"summary": content, "content_text": content}
            
        # Standardize for AnalysisResult
        final_data = {
            "summary": data.get("summary", ""),
            "abstract": data.get("content_text", ""),
            "keywords": data.get("keywords", []),
            "methodology": [],
            "technologies": [],
            "goal": data.get("goal", ""),
            "impact": "",
            "publication_year": data.get("publication_year", ""),
            "authors": data.get("authors", []),
            "statistics": {"word_count": len(data.get("content_text", "").split()), "unique_words": 0},
            "research_gaps": [],
            "conclusion": "",
            "content_text": data.get("content_text", "")
        }
        
        return final_data
        
    except Exception as e:
        logger.error(f"Groq Vision error: {e}", exc_info=True)
        return {
            "summary": f"Error analyzing image: {str(e)}",
            "content_text": "",
            "statistics": {"word_count": 0, "unique_words": 0}
        }