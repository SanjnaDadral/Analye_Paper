"""
Enhanced Analysis Response Builder
Creates structured, validated JSON responses for analysis results
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalysisResponseBuilder:
    """Builds structured analysis responses"""
    
    @staticmethod
    def build_success_response(analysis_data: Dict[str, Any], 
                              document_id: int, 
                              document_title: str,
                              input_type: str,
                              notices: List[str] = None) -> Dict[str, Any]:
        """Build success response with validated structure"""
        
        return {
            'success': True,
            'analysis': {
                'id': analysis_data.get('id'),
                'document_id': document_id,
                'title': document_title or analysis_data.get('title', 'Untitled'),
                'input_type': input_type,
                
                # Core metadata
                'metadata': {
                    'authors': analysis_data.get('authors', []),
                    'publication_year': analysis_data.get('publication_year', ''),
                    'word_count': analysis_data.get('statistics', {}).get('word_count', 0),
                    'unique_words': analysis_data.get('statistics', {}).get('unique_words', 0),
                },
                
                # Full analysis results
                'content': {
                    'title': document_title,
                    'abstract': analysis_data.get('abstract', ''),
                    'summary': analysis_data.get('summary', ''),
                    'keywords': analysis_data.get('keywords', []),
                    'goal': analysis_data.get('goal', ''),
                    'impact': analysis_data.get('impact', ''),
                    'conclusion': analysis_data.get('conclusion', ''),
                },
                
                # Technical analysis
                'technical': {
                    'technologies': analysis_data.get('technologies', []),
                    'methodology': analysis_data.get('methodology', []),
                    'methodology_summary': analysis_data.get('methodology_summary', ''),
                    'research_gaps': analysis_data.get('research_gaps', []),
                    'method_approach': analysis_data.get('method_approach', ''),
                },
                
                # Results and findings
                'results': {
                    'results_findings': analysis_data.get('results_findings', ''),
                    'limitations': analysis_data.get('limitations', ''),
                    'conclusion': analysis_data.get('conclusion', ''),
                },
                
                # Dataset details
                'dataset': {
                    'dataset_names': analysis_data.get('dataset_names', []),
                    'dataset_links': analysis_data.get('dataset_links', []),
                    'dataset_section': analysis_data.get('dataset_section', ''),
                    'dataset_size': analysis_data.get('dataset_size', ''),
                    'dataset_source': analysis_data.get('dataset_source', ''),
                    'extracted_links': analysis_data.get('extracted_links', []),
                    'references': analysis_data.get('references', []),
                },
                
                # Quality and assets
                'assets': {
                    'extracted_images': analysis_data.get('extracted_images', []),
                    'extracted_tables': analysis_data.get('extracted_tables', []),
                    'extracted_charts': analysis_data.get('extracted_charts', []),
                    'visual_assets': analysis_data.get('visual_assets', {}),
                },
                
                # Plagiarism check
                'plagiarism': analysis_data.get('plagiarism', {
                    'similarity_percent': 0.0,
                    'risk_level': 'low',
                    'matches': []
                }),
                
                # Paper metadata
                'paper_standard': analysis_data.get('paper_standard', 'General'),
                'url': analysis_data.get('url'),
                'created_at': analysis_data.get('created_at', datetime.now().isoformat()),
            },
            'notices': notices or [],
            'redirect_url': f'/result/{document_id}/'
        }
    
    @staticmethod
    def build_error_response(error_message: str, 
                            error_code: str = 'ANALYSIS_ERROR',
                            details: Dict = None) -> Dict[str, Any]:
        """Build error response"""
        
        return {
            'success': False,
            'error': error_message,
            'error_code': error_code,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def validate_analysis_data(analysis_data: Dict) -> tuple[bool, Optional[str]]:
        """Validate analysis data structure"""
        
        required_fields = ['keywords', 'summary', 'abstract', 'authors']
        missing_fields = [f for f in required_fields if f not in analysis_data]
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate data types
        validations = [
            ('keywords', list),
            ('authors', list),
            ('technologies', list),
            ('methodology', list),
        ]
        
        for field, expected_type in validations:
            if field in analysis_data:
                if not isinstance(analysis_data[field], expected_type):
                    return False, f"Field '{field}' must be {expected_type.__name__}"
        
        # Ensure keywords are not empty
        if not analysis_data.get('keywords'):
            return False, "At least one keyword must be extracted"
        
        return True, None
    
    @staticmethod
    def enrich_analysis_data(analysis_data: Dict, 
                            extracted_images: List = None,
                            extracted_tables: List = None, 
                            extracted_charts: List = None,
                            plagiarism_result: Dict = None) -> Dict[str, Any]:
        """Enrich analysis data with additional assets and metadata"""
        
        enriched = analysis_data.copy()
        
        # Add extracted assets
        enriched['extracted_images'] = extracted_images or []
        enriched['extracted_tables'] = extracted_tables or []
        enriched['extracted_charts'] = extracted_charts or []
        
        # Add plagiarism data
        enriched['plagiarism'] = plagiarism_result or {
            'similarity_percent': 0.0,
            'risk_level': 'low',
            'matches': [],
            'note': 'No plagiarism check performed'
        }
        
        # Calculate quality score (0-100)
        quality_components = {
            'abstract': min(100, len(enriched.get('abstract', '')) / 5),  # 500 chars = 100%
            'summary': min(100, len(enriched.get('summary', '')) / 2),     # 200 chars = 100%
            'keywords': min(100, len(enriched.get('keywords', [])) * 15),  # 10+ keywords = 100%
            'authors': min(100, len(enriched.get('authors', [])) * 20),    # 5+ authors = 100%
        }
        
        enriched['quality_score'] = int(sum(quality_components.values()) / len(quality_components))
        
        # Add processing timestamp
        enriched['processed_at'] = datetime.now().isoformat()
        
        return enriched


# Response helpers
def build_analysis_response(analysis_result, document, extracted_images=None, 
                           extracted_tables=None, extracted_charts=None,
                           plagiarism_result=None, notices=None):
    """Helper to build complete analysis response"""
    
    analysis_dict = {
        'id': analysis_result.id,
        'title': document.title,
        'summary': analysis_result.summary,
        'abstract': analysis_result.abstract,
        'keywords': analysis_result.keywords or [],
        'methodology': analysis_result.methodology or [],
        'technologies': analysis_result.technologies or [],
        'goal': analysis_result.goal,
        'impact': analysis_result.impact,
        'publication_year': analysis_result.publication_year,
        'authors': analysis_result.authors or [],
        'extracted_links': analysis_result.extracted_links or [],
        'dataset_names': analysis_result.dataset_names or [],
        'dataset_links': analysis_result.dataset_links or [],
        'references': analysis_result.references or [],
        'extracted_images': extracted_images or [],
        'extracted_tables': extracted_tables or [],
        'extracted_charts': extracted_charts or [],
        'plagiarism': plagiarism_result or {'similarity_percent': 0},
        'methodology_summary': analysis_result.extras.get('methodology_summary', ''),
        'visual_assets': analysis_result.extras.get('visual_assets', {}),
        'paper_standard': analysis_result.extras.get('paper_standard', ''),
        'statistics': {
            'word_count': analysis_result.word_count,
            'unique_words': analysis_result.unique_words,
        },
        'created_at': analysis_result.created_at.strftime('%B %d, %Y at %H:%M'),
        'url': document.url,
    }
    
    return AnalysisResponseBuilder.build_success_response(
        analysis_dict,
        document.id,
        document.title,
        document.input_type,
        notices
    )
