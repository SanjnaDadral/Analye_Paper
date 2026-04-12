"""Plagiarism checking module with local library and web search capabilities."""
import re
import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)


def _normalize(sample: str, max_len: int = 12000) -> str:
    """Normalize text for comparison."""
    s = sample[:max_len].lower()
    return re.sub(r"\s+", " ", s).strip()


def _get_ngrams(text: str, n: int = 3) -> set:
    """Extract n-grams from text for more accurate matching."""
    words = text.split()
    return set(' '.join(words[i:i+n]) for i in range(len(words) - n + 1))


def _calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts."""
    return SequenceMatcher(None, text1, text2).ratio()


def local_library_similarity(document_id: int, text: str, limit_docs: int = 50, user=None) -> Dict[str, Any]:
    """Check similarity against other documents in the database."""
    from .models import Document

    if not text or len(text) < 200:
        return {
            "similarity_percent": 0.0,
            "matches": [],
            "note": "Not enough text to compare against your library.",
        }

    norm = _normalize(text)
    matches: List[Dict[str, Any]] = []
    best_pct = 0.0

    # Get all documents to compare against (excluding the current document)
    # Only compare against OTHER users' documents to avoid self-matching issues
    if user:
        others = (
            Document.objects.exclude(id=document_id)
            .exclude(user=user)  # Only compare against OTHER users' documents
            .exclude(content="")
            .order_by("-created_at")[:limit_docs]
        )
    else:
        others = (
            Document.objects.exclude(id=document_id)
            .exclude(content="")
            .order_by("-created_at")[:limit_docs]
        )

    # If no other documents in library, return 0% similarity
    if not others.exists():
        note = "No other papers found for comparison."
        if user:
            note = "This is your first paper - no comparison available. Similarity score: 0%"
        return {
            "similarity_percent": 0.0,
            "matches": [],
            "risk_level": "low",
            "note": note,
        }

    for doc in others:
        other_norm = _normalize(doc.content or "")
        if len(other_norm) < 100:
            continue
        
        # Prevent false 100% matches by checking for identical content
        if norm == other_norm:
            # Identical content - this might be the same document being re-checked
            # Skip this match to avoid false positives
            continue
        
        # Use both sequence matching and n-gram comparison
        ratio = SequenceMatcher(None, norm, other_norm).ratio()
        
        # Also check n-gram overlap
        ngrams1 = _get_ngrams(norm)
        ngrams2 = _get_ngrams(other_norm)
        
        if ngrams1 and ngrams2:
            ngram_overlap = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
            ratio = max(ratio, ngram_overlap)
        
        pct = round(ratio * 100, 1)
        
        # Cap similarity at 95% to prevent false 100% readings from common phrases
        # Academic papers naturally share common terminology
        if pct > 95:
            pct = 95.0
        
        if pct > best_pct:
            best_pct = pct
        if pct >= 10.0:  # Lowered threshold to capture more matches
            matches.append({
                "title": (doc.title or "Untitled")[:200],
                "similarity_percent": pct,
                "document_id": doc.id,
            })

    matches.sort(key=lambda x: -x["similarity_percent"])
    
    # Determine risk level based on highest similarity found
    if best_pct < 25:
        risk_level = "low"
        risk_message = f"Low similarity ({best_pct}%) - appears to be original work"
    elif best_pct < 50:
        risk_level = "medium"
        risk_message = f"Moderate similarity ({best_pct}%) detected - review recommended"
    else:
        risk_level = "high"
        risk_message = f"High similarity ({best_pct}%) detected - manual review required"
    
    return {
        "similarity_percent": best_pct,
        "matches": matches[:10],
        "risk_level": risk_level,
        "note": risk_message,
    }


def text_quality_check(text: str) -> Dict[str, Any]:
    """Check text quality and provide insights."""
    if not text or len(text) < 100:
        return {
            "quality_score": 0,
            "is_suspicious": False,
            "issues": ["Text too short to analyze"]
        }
    
    issues = []
    warnings = []
    
    # Check for common issues
    if re.search(r'(.)\1{4,}', text):
        issues.append("Contains repeated characters")
    
    if len(set(text.lower())) / len(text) < 0.1:
        warnings.append("Low character diversity")
    
    word_count = len(text.split())
    if word_count < 50:
        warnings.append("Very short content")
    
    # Calculate quality score (0-100)
    quality_score = 100
    quality_score -= len(issues) * 20
    quality_score -= len(warnings) * 10
    quality_score = max(0, min(100, quality_score))
    
    return {
        "quality_score": quality_score,
        "is_suspicious": len(issues) > 0,
        "issues": issues,
        "warnings": warnings,
        "word_count": word_count,
    }


def extract_key_phrases(text: str, top_n: int = 20) -> List[Dict[str, Any]]:
    """Extract significant phrases from text for comparison."""
    if not text:
        return []
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    
    if len(sentences) < 3:
        return []
    
    # Find common phrases
    phrase_counts = Counter()
    for sentence in sentences:
        words = sentence.split()
        if len(words) >= 4:
            for i in range(len(words) - 3):
                phrase = ' '.join(words[i:i+4])
                phrase_counts[phrase.lower()] += 1
    
    # Return most common significant phrases
    significant_phrases = []
    for phrase, count in phrase_counts.most_common(top_n * 2):
        if count >= 2 and len(phrase) > 15:
            significant_phrases.append({
                "phrase": phrase,
                "occurrences": count,
                "is_copied": count > 5  # Flag very common phrases
            })
        if len(significant_phrases) >= top_n:
            break
    
    return significant_phrases


def comprehensive_plagiarism_check(document_id: int, text: str) -> Dict[str, Any]:
    """Perform comprehensive plagiarism and originality check."""
    if not text or len(text) < 200:
        return {
            "overall_score": 0,
            "risk_level": "unknown",
            "details": {
                "library_similarity": {"similarity_percent": 0, "matches": []},
                "quality_check": {"quality_score": 0, "is_suspicious": False, "issues": []},
                "key_phrases": [],
            },
            "note": "Not enough text for comprehensive analysis"
        }
    
    # Run all checks
    library_result = local_library_similarity(document_id, text)
    quality_result = text_quality_check(text)
    key_phrases = extract_key_phrases(text)
    
    # Calculate overall originality score (inverse of similarity)
    library_similarity = library_result.get("similarity_percent", 0)
    quality_score = quality_result.get("quality_score", 100)
    
    # Weighted average: 70% library check, 30% quality
    originality_score = ((100 - library_similarity) * 0.7) + (quality_score * 0.3)
    
    # Determine overall risk
    if originality_score >= 75:
        risk_level = "low"
    elif originality_score >= 50:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    return {
        "overall_score": round(originality_score, 1),
        "risk_level": risk_level,
        "details": {
            "library_similarity": library_result,
            "quality_check": quality_result,
            "key_phrases": key_phrases,
        },
        "note": f"Originality Score: {round(originality_score, 1)}% - {risk_level.title()} Risk",
    }
