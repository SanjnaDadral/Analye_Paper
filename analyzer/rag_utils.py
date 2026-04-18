import json
import logging
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

# def rag_pipeline(text: str, query: str = "Summarize this research paper"):
#     """Main fast Groq analysis function used by your views"""
#     try:
#         text = text or ""
#         if len(text.strip()) < 20:
#             return "Not enough content in the document to analyze."

#         client = Groq(api_key=settings.GROQ_API_KEY)

#         # Take beginning + end for better context
#         # context = (text[:25000] + "\n...\n" + text[-15000:]) if len(text) > 40000 else text

#         MAX_CHARS = 12000   # safe limit

#         if len(text) > MAX_CHARS:
#                 context = text[:6000] + "\n...\n" + text[-6000:]
#         else:
#             context = text

#         prompt = f"""
# You are an expert research assistant.

# CONTEXT:
# {context}

# QUESTION:
# {query}

# INSTRUCTIONS:
# - Provide a clear, structured answer.
# - Use bullet points where helpful.
# - If information is not in the context, clearly mention it.
# """

#         response = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[
#                 {"role": "system", "content": "You are an expert academic research assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=2000,
#         )

#         # return response.choices[0].message.content
#         return {
#              "summary": response.choices[0].message.content
#             }
#     except Exception as e:
#         logger.error("GROQ Pipeline Error", exc_info=True)
#         return f"Error analyzing the paper: {str(e)}"

def rag_pipeline(text: str, query: str = "Summarize this research paper"):
    try:
        text = text or ""
        if len(text.strip()) < 20:
            return {"summary": "Not enough content in the document to analyze."}

        client = Groq(api_key=settings.GROQ_API_KEY)

        # ✅ SAFE CONTEXT LIMIT
        MAX_CHARS = 3000
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
    """Returns a dict with structured analysis keys — never a plain str."""
    word_count = len(text.split())
    unique_words = len(set(text.split()))
    _safe_dict = lambda summary: {
        "summary": summary, "abstract": "", "keywords": [], "methodology": [],
        "technologies": [], "goal": "", "impact": "", "publication_year": "",
        "authors": [], "research_gaps": [], "conclusion": "",
        "statistics": {"word_count": word_count, "unique_words": unique_words},
    }
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        context = text[:2000]
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. Keys: summary, abstract, keywords(array), methodology(array), technologies(array), goal, impact, publication_year, authors(array), research_gaps(array), conclusion. No markdown."},
                {"role": "user", "content": f"Analyze:\n\n{context}"},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        raw_content = response.choices[0].message.content.strip()
        stripped = raw_content
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[-1]
            stripped = stripped[:stripped.rfind("```")].strip() if "```" in stripped else stripped
        try:
            data = json.loads(stripped)
            if not isinstance(data, dict):
                return _safe_dict(stripped[:500])
            data["statistics"] = {"word_count": word_count, "unique_words": unique_words}
            return data
        except json.JSONDecodeError:
            return _safe_dict(raw_content[:500])
    except Exception as e:
        logger.error(f"analyze_text_with_groq Error: {str(e)}", exc_info=True)
        return _safe_dict(f"Error: {str(e)}")