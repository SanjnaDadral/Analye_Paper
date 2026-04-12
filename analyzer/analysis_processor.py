"""
Analysis Processor - Orchestrates the complete paper analysis pipeline
Handles: PDF extraction → Text cleaning → Section detection → NLP processing → JSON response
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalysisProcessor:
    """Orchestrates the complete analysis pipeline"""
    
    def __init__(self):
        from analyzer.nlp_processor import nlp_processor
        from analyzer.pdf_processor import pdf_processor
        self.nlp = nlp_processor
        self.pdf = pdf_processor
    
    def analyze_document(self, content: str, input_type: str = 'pdf', 
                        filename: str = '', **kwargs) -> Dict[str, Any]:
        """
        Complete analysis pipeline
        
        Args:
            content: Extracted text from document
            input_type: 'pdf', 'text', or 'url'
            filename: Original filename
            
        Returns:
            Structured JSON-serializable analysis result
        """
        
        if not content or len(content.strip()) < 50:
            return self._error_response("Document is empty or too short for analysis")
        
        try:
            # Clean text
            clean_text = self._clean_text(content)
            
            # Extract metadata
            title = self.nlp.extract_title(clean_text)
            authors = self.nlp.extract_authors(clean_text)
            year = self.nlp.extract_year(clean_text)
            abstract = self.nlp.extract_abstract(clean_text)
            
            # NLP Analysis
            keywords = self.nlp.extract_keywords(clean_text, top_n=15)
            summary = self.nlp.generate_summary(clean_text, max_length=200)
            
            # Detection
            technologies = self.nlp.detect_technologies(clean_text)
            methodology = self.nlp.detect_methodology(clean_text)
            dataset_info = self.nlp.extract_dataset_info(clean_text)
            
            # Additional analytics
            word_count = len(clean_text.split())
            sentence_count = len([s for s in clean_text.split('.') if len(s.strip()) > 5])
            
            # Confidence scores
            confidence_scores = self._calculate_confidence(
                title, authors, abstract, keywords
            )
            
            result = {
                'success': True,
                'metadata': {
                    'title': title or 'Untitled Research Paper',
                    'authors': authors,
                    'year': year,
                    'input_type': input_type,
                    'processed_at': datetime.now().isoformat(),
                    'word_count': word_count,
                    'sentence_count': sentence_count,
                },
                'analysis': {
                    'abstract': abstract,
                    'summary': summary,
                    'keywords': keywords,
                    'technologies': technologies,
                    'methodology': methodology,
                    'dataset_link': dataset_info,
                },
                'quality_metrics': {
                    'title_confidence': confidence_scores['title'],
                    'abstract_confidence': confidence_scores['abstract'],
                    'keywords_confidence': confidence_scores['keywords'],
                    'overall_quality': confidence_scores['overall'],
                    'analysis_completeness': self._calculate_completeness(
                        title, abstract, summary, keywords
                    ),
                },
                'source_stats': {
                    'total_chars': len(clean_text),
                    'avg_word_length': word_count / max(len(clean_text.split()), 1),
                    'sections_detected': self._detect_sections(clean_text),
                }
            }
            
            logger.info(f"✓ Analysis completed: {result['metadata'].get('title', 'Untitled')}")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return self._error_response(f"Analysis failed: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove common artifacts
        text = re.sub(r'(?i)page\s*\d+', '', text)
        text = re.sub(r'[^\w\s\.\,\-\:\;\!\?\(\)\[\]\n]', '', text)
        
        return text.strip()
    
    def _detect_sections(self, text: str) -> List[str]:
        """Detect paper sections"""
        import re
        sections = []
        section_keywords = [
            'abstract', 'introduction', 'background', 'literature', 'related work',
            'methodology', 'method', 'approach', 'experiment', 'result', 'conclusion',
            'discussion', 'future work', 'reference', 'appendix'
        ]
        
        for keyword in section_keywords:
            if re.search(r'(?i)(?:^|\n)\s*' + keyword, text):
                sections.append(keyword)
        
        return sections
    
    def _calculate_confidence(self, title: str, authors: List[str], 
                            abstract: str, keywords: List[str]) -> Dict[str, float]:
        """Calculate confidence scores for extracted metadata"""
        
        def normalize_score(value, min_len=0, max_len=100):
            if isinstance(value, list):
                length = len(value)
            else:
                length = len(value) if value else 0
            
            if length >= max_len:
                return 1.0
            elif length <= min_len:
                return 0.0
            else:
                return (length - min_len) / (max_len - min_len)
        
        scores = {
            'title': 0.9 if title and len(title) > 10 else 0.3,
            'abstract': normalize_score(abstract, min_len=100, max_len=1000),
            'keywords': normalize_score(keywords, min_len=5, max_len=15),
            'authors': normalize_score(authors, min_len=1, max_len=10),
        }
        
        scores['overall'] = sum(scores.values()) / len(scores)
        return {k: round(v, 2) for k, v in scores.items()}
    
    def _calculate_completeness(self, title: str, abstract: str, 
                               summary: str, keywords: List[str]) -> int:
        """Calculate analysis completeness percentage"""
        components_found = 0
        components_total = 4
        
        if title and len(title) > 5:
            components_found += 1
        if abstract and len(abstract) > 50:
            components_found += 1
        if summary and len(summary) > 30:
            components_found += 1
        if keywords and len(keywords) > 3:
            components_found += 1
        
        return int((components_found / components_total) * 100)
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            'success': False,
            'error': error_message,
            'metadata': {},
            'analysis': {},
            'quality_metrics': {}
        }


# Global instance
analysis_processor = AnalysisProcessor()
