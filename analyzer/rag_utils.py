import logging
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

# =========================
# 🚀 OPTIMIZED Q&A PIPELINE
# =========================
# def rag_pipeline(text, query="Summarize this research paper"):
#     """
#     Simplified Q&A pipeline for research papers.
#     Instead of slow local embeddings (RAG), we use GROQ's large context window (128k)
#     directly. This provides 10x faster responses for papers up to 50k characters.
#     """
#     try:
#         client = Groq(api_key=settings.GROQ_API_KEY)
        
#         # Limit text to ~30k chars to ensure we stay well within context limits
#         # while preserving most of the paper's content.
#         context = text[:35000]
        
#         prompt = f"""
#         Analyze the research paper context provided below and answer the specific question. 
#         If the information is not in the context, use your general knowledge but mention it's not explicitly in the paper.
        
#         CONTEXT:
#         {context}
        
#         QUESTION:
#         {query}
        
#         INSTRUCTIONS:
#         - Provide a clear, detailed, and structured answer.
#         - Use bullet points for lists.
#         - Be concise but thorough.
#         """
        
#         response = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[
#                 {"role": "system", "content": "You are an expert research assistant specialized in academic paper analysis."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=1500
#         )
        
#         return response.choices[0].message.content
        
#     except Exception as e:
#         logger.error(f"GROQ Q&A Pipeline Error: {str(e)}")
#         return f"I encountered an error while analyzing the paper: {str(e)}"

from groq import Groq
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def rag_pipeline(text, query="Summarize this research paper"):
    """
    Fast Groq-based RAG pipeline for research paper Q&A.
    """

    try:
        # SAFE fallback for None
        text = text or ""

        if len(text.strip()) < 20:
            return "Not enough content in document to analyze."

        client = Groq(api_key=settings.GROQ_API_KEY)

        # limit context safely
        # context = text[:35000]
        text = text[-35000:] + text[:35000]
        prompt = f"""
        You are an expert research assistant.

        CONTEXT:
        {context}

        QUESTION:
        {query}

        INSTRUCTIONS:
        - Answer only based on context when possible.
        - Be structured and clear.
        - Use bullet points if needed.
        - If not found in context, mention it clearly.
        """

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert academic research assistant."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        return response.choices[0].message.content

    # except Exception as e:
    #     logger.error(f"GROQ Q&A Pipeline Error: {str(e)}", exc_info=True)
    #     return "Sorry, I encountered an error while analyzing this document."
    except Exception as e:
        logger.error("GROQ Q&A Pipeline Error", exc_info=True)

    return {
        "success": False,
        "error": "GROQ_PIPELINE_FAILED",
        "message": "Unable to process document",
        "details": str(e)  # only for backend logs or debug mode
    }
# Keep these stubs for compatibility if needed elsewhere, but they aren't used for the main speedup
def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def get_embeddings(chunks):
    return []

def create_faiss_index(embeddings):
    return None

def search_chunks(query, chunks, index, top_k=5):
    return chunks[:top_k]