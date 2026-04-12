import re
import logging
import os
from typing import Dict, List, Any
from collections import Counter
import json

logger = logging.getLogger(__name__)

# NLTK setup
try:
    import nltk
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except Exception as e:
    logger.warning(f"NLTK not available: {e}")
    NLTK_AVAILABLE = False

# sklearn setup
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"sklearn not available: {e}")
    SKLEARN_AVAILABLE = False
    TfidfVectorizer = None
    np = None


class MLProcessor:
    def __init__(self):
        self._models_loaded = False
        self._stop_words = None
        
        if NLTK_AVAILABLE:
            try:
                self._stop_words = set(stopwords.words('english'))
            except:
                self._stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        else:
            self._stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}

    def _load_models(self):
        if self._models_loaded:
            return
        self._models_loaded = True
        logger.info("✓ MLProcessor initialized with TF-IDF (sklearn) + fallback methods")

    def _get_stop_words(self):
        if self._stop_words is None:
            self._stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        return self._stop_words

    def extract_authors(self, text: str) -> List[str]:
        """Extract author names from text."""
        authors = set()
        first_15k = text[:15000]
        
        # Pattern 1: "Authors: Name Name" or "Author: Name Name"
        patterns = [
            r'(?:author|authors|by)[:\s]+([^\n]+)',
        ]
        
        for pat in patterns:
            matches = re.findall(pat, first_15k, re.IGNORECASE)
            for m in matches:
                # Split by commas or 'and' to get individual names
                name_parts = re.split(r'[,;]|\s+and\s+|\s+&\s+', m)
                for name in name_parts:
                    name = name.strip()
                    if self._is_valid_name(name):
                        authors.add(name)
        
        # Pattern 2: Multiple capitalized words (common name format)
        # Look near the title area
        title_area = text[:5000]
        lines = title_area.split('\n')
        for line in lines[:10]:
            line = line.strip()
            # Skip if it's the title (too long) or abstract
            if len(line) > 80 or len(line) < 5:
                continue
            # Skip common false positives
            skip_words = ['abstract', 'introduction', 'background', 'keywords', 'doi', 'http', 'email', 'university', 'department', 'school', 'institute', 'received', 'revised', 'accepted', 'published']
            if any(skip in line.lower() for skip in skip_words):
                continue
            # Match potential names: "First Last" or "First Middle Last"
            name_matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b', line)
            for name in name_matches:
                if self._is_valid_name(name) and len(name) > 4:
                    authors.add(name)
        
        # Filter out false positives
        false_positives = {
            'Abstract', 'Introduction', 'References', 'Conclusion', 'Figure', 'Table', 
            'Email', 'https', 'http', 'University', 'Department', 'School', 'Institute',
            'Received', 'Revised', 'Accepted', 'Published', 'Copyright', 'Journal',
            'Volume', 'Issue', 'Pages', 'doi', 'DOI', 'Academic', 'Editor', 'Editors',
            'Keywords', 'Abstract', 'Background', 'Methodology', 'Results', 'Discussion'
        }
        authors = {a for a in authors if a not in false_positives and len(a) > 3 and len(a) < 60}
        
        # Additional filter: remove if contains numbers or special chars
        final_authors = []
        for a in authors:
            if re.match(r'^[A-Za-z\s\.\-]+$', a) and not any(c.isdigit() for c in a):
                final_authors.append(a)
        
        return sorted(final_authors)[:10]

    def _is_valid_name(self, name: str) -> bool:
        """Check if text looks like a person name."""
        name = name.strip()
        if not name or len(name) < 4 or len(name) > 40:
            return False
        if not re.match(r'^[A-Za-z\s\.\-]+$', name):
            return False
        parts = name.split()
        if len(parts) < 2:
            return False
        for p in parts:
            if not (p[0].isupper() or (len(p) == 2 and p[1] == '.')):
                return False
        return True

    def extract_publication_year(self, text: str) -> str:
        """Extract publication year with improved patterns."""
        # Priority patterns (most specific first)
        patterns = [
            # Standard publication phrases
            r'(?:published|accepted|presented|submitted|revised)[\s:]+(?:in\s+)?(\d{4})',
            r'(?:published|published online)[\s:]+(?:[\w\s]+)?(\d{4})',
            # Copyright
            r'©\s*(\d{4})',
            r'Copyright\s+(\d{4})',
            r'©\s*20\d{2}',
            # arXiv patterns
            r'arXiv:\d+\.\d+\s+\[.*?\]\s+(\d{4})',
            r'arXiv:\d+\.\d+\s+\((\d{4})\)',
            # DOI pattern
            r'doi:10\.\d+/.+?(\d{4})',
            # Date patterns in various formats
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(\d{4})',
            r'(\d{1,2})\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
            # Received/Revised dates (usually earlier than publication)
            r'(?:received|revised)[\s:]+(?:[\w\s]+)?(\d{4})',
            # Year in citations
            r'\[\d{4}\]|\(\d{4}\)|(?:19|20)\d{2}',
        ]
        
        best_year = None
        
        for pat in patterns:
            matches = re.findall(pat, text[:20000], re.IGNORECASE)
            if matches:
                for match in matches:
                    # Handle tuple matches
                    if isinstance(match, tuple):
                        for m in match:
                            if m and m.isdigit() and len(m) == 4:
                                year = int(m)
                                if 1990 <= year <= 2030:
                                    if best_year is None or year > best_year:
                                        best_year = year
                    # Handle string matches
                    elif match.isdigit() and len(match) == 4:
                        year = int(match)
                        if 1990 <= year <= 2030:
                            if best_year is None or year > best_year:
                                best_year = year
        
        return str(best_year) if best_year else ""

    def extract_abstract(self, text: str) -> str:
        """Extract abstract section - improved detection with fallback."""
        labeled = self._extract_labeled_abstract(text)
        if labeled and len(labeled) > 100:
            return labeled
        
        first_8k = text[:8000]
        paragraphs = re.split(r'\n\s*\n', first_8k)
        
        for i, para in enumerate(paragraphs):
            para = para.strip()
            para_lower = para.lower()
            
            if len(para) > 150 and len(para) < 3000:
                if not re.search(r'^(introduction|background|related work|methodology|experiments|results|discussion)', para_lower):
                    if not para_lower.startswith(('1.', '2.', '3.', 'figure', 'table', 'http', '-', '*')):
                        return para[:3000]
        
        sentences = re.split(r'(?<=[.!?])\s+', first_8k)
        abstract_candidates = []
        for sent in sentences:
            sent = sent.strip()
            if 40 < len(sent) < 400:
                if not re.search(r'(?i)(introduction|background|methodology|results|conclusion|reference)', sent):
                    abstract_candidates.append(sent)
        
        if len(abstract_candidates) >= 2:
            return ' '.join(abstract_candidates[:5])[:3000]
        
        # If no abstract found, try to infer/generate one
        return self._infer_abstract(text)
    
    def _infer_abstract(self, text: str) -> str:
        """Generate an abstract-like summary from paper content when none exists."""
        text_sample = text[:15000]
        
        # Extract key components
        title = self.extract_title(text_sample)
        goal = self.extract_goal(text_sample)
        keywords = self.extract_keywords(text_sample, top_n=8)
        methodology = self.detect_methodology(text_sample)
        
        # Try to extract from introduction (first substantial paragraph after title)
        intro_paragraphs = []
        lines = text_sample.split('\n\n')
        found_intro = False
        
        for para in lines:
            para_lower = para.lower().strip()
            if 'introduction' in para_lower and len(para_lower) < 50:
                found_intro = True
                continue
            if found_intro and len(para) > 100 and len(para) < 1500:
                if not para_lower.startswith(('1.', '2.', 'figure', 'table', 'http')):
                    intro_paragraphs.append(para.strip())
                    if len(intro_paragraphs) >= 2:
                        break
        
        if intro_paragraphs:
            abstract = ' '.join(intro_paragraphs[:2])
            if len(abstract) > 100:
                return abstract[:3000]
        
        # Fallback: construct from available components
        abstract_parts = []
        
        if title:
            abstract_parts.append(f"This paper presents research on {title[:100]}.")
        
        if goal:
            abstract_parts.append(f"The primary goal of this study is to {goal[:150]}.")
        
        if methodology:
            methods = ', '.join(methodology[:4])
            abstract_parts.append(f"The approach employs {methods} methodologies to address the research objectives.")
        
        if keywords:
            kw_str = ', '.join(keywords[:6])
            abstract_parts.append(f"Key topics include {kw_str}.")
        
        # Add general context from text
        text_lower = text_sample.lower()
        
        if any(w in text_lower for w in ['problem', 'challenge', 'issue']):
            abstract_parts.append("This research addresses significant challenges in the domain.")
        
        if any(w in text_lower for w in ['propose', 'present', 'introduce', 'develop']):
            abstract_parts.append("The proposed methods aim to advance current understanding and capabilities.")
        
        if any(w in text_lower for w in ['result', 'finding', 'show', 'demonstrate']):
            abstract_parts.append("The findings contribute valuable insights to the field.")
        
        if abstract_parts:
            return ' '.join(abstract_parts)
        
        return ""

    def _extract_labeled_abstract(self, text: str) -> str:
        """Search for labeled abstract section."""
        patterns = [
            r'(?i)(?:^|\n)\s*abstract\s*[:.-]*\s*\n+([\s\S]{100,4000}?)(?=\n\s*\n|\n\s*(?:keywords?|1\.|introduction))',
            r'(?i)(?:^|\n)\s*abstract\s*\n-+\n([\s\S]{100,4000}?)(?=\n\s*\n)',
            r'(?i)<abstract>([\s\S]{100,4000}?)</abstract>',
            r'(?i)(?:^|\n)\s*summary\s*[:.-]*\s*\n+([\s\S]{100,4000}?)(?=\n\s*\n|\n\s*(?:keywords?|1\.|introduction))',
            r'(?i)^abstract[:.\s]+([\s\S]{100,4000}?)(?=\n\s*(?:introduction|keywords|1\.)|\n\n|$)',
            r'(?i)^\s*abstract[:.\s]+([\s\S]{50,3000})(?:(?=\n\s*\n)|(?=\n\s*(?:introduction|keywords|1\.))|$)',
        ]
        
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                abstract = m.group(1).strip()
                abstract = re.sub(r'\s+', ' ', abstract)
                if 100 < len(abstract) < 4000:
                    return abstract
        return ""

    def extract_conclusion(self, text: str) -> str:
        """Extract conclusion section - improved detection."""
        text_lower = text.lower()
        
        patterns = [
            r'(?i)(?:^|\n)\s*(?:conclusion|conclusions?|final remarks|summary and conclusions?)\s*[:.-]*\s*\n+([\s\S]{100,5000}?)(?=\n\s*\n|\n\s*(?:references|bibliography|acknowledgments?|appendix))',
            r'(?i)(?:^|\n)\s*conclusion\s*\n-+\n([\s\S]{100,5000}?)(?=\n\s*\n)',
            r'(?i)(?:^|\n)\s*(?:conclusion|conclusions?)\s*\n([\s\S]{100,4000}?)(?=\n\s*(?:references|bibliography))',
            r'(?i)(?:^|\n)\s*(?:5\.|V\.|5\s)\s*(?:conclusion|conclusions?)\s*\n([\s\S]{100,5000}?)(?=\n\s*\n)',
            r'(?i)(?:^|\n)\s*(?:conclusion)\s*[:.\-]*\n([\s\S]{80,3000})',
        ]
        
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                conclusion = m.group(1).strip()
                conclusion = re.sub(r'\s+', ' ', conclusion)
                if 80 < len(conclusion) < 5000:
                    return conclusion[:4000]
        
        sections = re.split(r'\n\s*\n', text)
        for i in range(len(sections)-1, max(0, len(sections)-8), -1):
            section = sections[i].strip()
            section_lower = section.lower()
            if 'conclusion' in section_lower or '5' in section_lower[:20]:
                if len(section) > 80 and len(section) < 5000:
                    cleaned = re.sub(r'^(conclusion|conclusions?)\s*[:.\-]*\s*', '', section, flags=re.IGNORECASE)
                    if len(cleaned) > 50:
                        return cleaned[:4000]
        
        last_para = text.split('\n\n')[-1]
        if last_para:
            last_para = last_para.strip()
            if len(last_para) > 50 and len(last_para) < 2000:
                if re.search(r'(?i)(conclude|future work|final|summary)', last_para):
                    return last_para
        
        return ""

    def extract_native_summary(self, text: str) -> str:
        """Extract the paper's own summary."""
        patterns = [
            r'(?i)(?:^|\n)\s*(?:summary|executive summary)\s*[:.-]*\s*\n+([\s\S]{200,4000}?)(?=\n\s*\n|\n(?=[A-Z]))',
            r'(?i)(?:^|\n)\s*summary\s*\n-+\n([\s\S]{200,4000}?)(?=\n\s*\n)',
        ]
        
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                summary = m.group(1).strip()
                summary = re.sub(r'\s+', ' ', summary)
                if len(summary) > 100:
                    return summary[:3500]
        
        return self.extract_conclusion(text)

    def extract_keywords(self, text: str, top_n: int = 15) -> List[str]:
        """Extract keywords using TF-IDF (sklearn) with frequency fallback."""
        self._load_models()
        
        keyword_section = self._extract_keyword_section(text)
        if keyword_section:
            return keyword_section[:top_n]
        
        return self._tfidf_keyword_extraction(text, top_n)

    def _tfidf_keyword_extraction(self, text: str, top_n: int = 15) -> List[str]:
        """Extract keywords using TF-IDF with sklearn, fallback to frequency."""
        if not text or len(text) < 100:
            return []
        
        text_sample = text[:30000]
        
        if SKLEARN_AVAILABLE and TfidfVectorizer is not None:
            try:
                sentences = re.split(r'(?<=[.!?])\s+', text_sample)
                sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                
                if len(sentences) < 3:
                    sentences = text_sample.split('\n')
                
                sentences = [s for s in sentences if len(s) > 20]
                if not sentences:
                    return self._basic_keyword_extraction(text, top_n)
                
                vectorizer = TfidfVectorizer(
                    max_features=100,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.8
                )
                
                try:
                    matrix = vectorizer.fit_transform(sentences)
                    if np is not None:
                        scores = matrix.sum(axis=0).A1
                        terms = vectorizer.get_feature_names_out()
                        top_indices = np.argsort(scores)[-top_n * 2:][::-1]
                        keywords = [terms[i] for i in top_indices if scores[i] > 0]
                        if keywords:
                            return keywords[:top_n]
                except Exception as e:
                    logger.warning(f"TF-IDF extraction failed: {e}")
            except Exception as e:
                logger.warning(f"TF-IDF setup failed: {e}")
        
        return self._basic_keyword_extraction(text, top_n)

    def _basic_keyword_extraction(self, text: str, top_n: int = 15) -> List[str]:
        """Fallback keyword extraction using frequency analysis."""
        if len(text) > 15000:
            text = text[:15000]
        
        stop_words = self._get_stop_words()
        
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        filtered_words = [w for w in words if w not in stop_words]
        word_freq = Counter(filtered_words)
        
        return [word.title() for word, count in word_freq.most_common(top_n)]

    def _extract_keyword_section(self, text: str) -> List[str]:
        """Extract keywords from dedicated keywords section."""
        patterns = [
            r'(?i)(?:keywords?|key ?terms?|index ?terms?)\s*[:.-]*\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\n|\n\s*(?:1\.|introduction|abstract))',
            r'(?i)(?:CCS\s+CONCEPTS?\s*:\s*)([^\n]+)',
        ]
        
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                keyword_text = m.group(1).strip()
                keywords = re.split(r'[,;•·\n]', keyword_text)
                cleaned = []
                for kw in keywords:
                    kw = kw.strip().lower()
                    kw = re.sub(r'^\d+\.\s*', '', kw)
                    kw = re.sub(r'^\*\s*', '', kw)
                    if 2 < len(kw) < 50 and not kw.startswith('http'):
                        cleaned.append(kw.title())
                if cleaned:
                    return cleaned
        return []

    def detect_methodology(self, text: str) -> List[str]:
        """Detect research methodology from methodology section only."""
        method_section = self._extract_methodology_section(text)
        
        if not method_section:
            method_section = text[:20000]
        
        method_keywords = {
            'Experimental': ['experiment', 'experimental setup', 'case study', 'benchmark', 'evaluation metrics', 'performance evaluation', 'we collected', 'we used', 'data were collected', 'samples were'],
            'Statistical Analysis': ['statistical analysis', 'hypothesis test', 'anova', 'regression analysis', 'p-value', 'bayesian', 'correlation', 'chi-square', 'multivariate', 'statistically significant'],
            'Machine Learning': ['machine learning', 'supervised', 'unsupervised', 'random forest', 'svm', 'support vector machine', 'decision tree', 'knn', 'k-nearest', 'xgboost', 'logistic regression', 'naive bayes', 'gradient boosting', 'classification', 'regression model'],
            'Deep Learning': ['deep learning', 'neural network', 'neural networks', 'cnn', 'rnn', 'lstm', 'gru', 'transformer', 'attention mechanism', 'gan', 'autoencoder', 'encoder-decoder', 'bert', 'gpt', 'convolutional'],
            'NLP': ['nlp', 'natural language processing', 'language model', 'text classification', 'ner', 'named entity recognition', 'sentiment analysis', 'text mining', 'word embedding', 'tokenization', 'corpus', 'corpora'],
            'Computer Vision': ['computer vision', 'object detection', 'image segmentation', 'resnet', 'yolo', 'opencv', 'image classification', 'feature extraction', 'image processing', 'image analysis'],
            'Reinforcement Learning': ['reinforcement learning', 'rl', 'q-learning', 'policy gradient', 'dqn', 'actor-critic', 'reward function', 'agent', 'environment'],
            'Data Mining': ['data mining', 'association rule', 'clustering', 'k-means', 'hierarchical clustering', 'outlier detection', 'data preprocessing'],
            'Survey': ['survey', 'literature review', 'systematic review', 'meta-analysis', 'qualitative analysis', 'questionnaire', 'interview'],
            'Epidemiological': ['epidemiological', 'cohort study', 'case-control', 'cross-sectional', 'longitudinal', 'population', 'health survey', 'exposure assessment'],
            'Chemical Analysis': ['chemical analysis', 'chromatography', 'spectroscopy', 'mass spectrometry', 'gc-ms', 'hplc', 'ppm', 'µg/m³', 'pm2.5', 'pm10'],
            'Geospatial Analysis': ['gis', 'geographic information system', 'spatial analysis', 'geospatial', 'remote sensing', 'satellite'],
            'Time Series Analysis': ['time series', 'arima', 'forecasting', 'temporal', 'seasonal', 'trend analysis'],
        }
        
        detected = []
        text_lower = method_section.lower()
        
        for method, kw_list in method_keywords.items():
            matches = sum(1 for kw in kw_list if kw in text_lower)
            if matches >= 1:
                detected.append(method)
        
        if not detected:
            detected.append('Research Study')
        
        return detected[:8]

    def _extract_methodology_section(self, text: str) -> str:
        """Extract methodology section text."""
        section_match = re.search(
            r'(?i)(?:^|\n)(?:methodology|methods|approach|experimental setup|proposed method|materials?)\s*[:.-]*\s*\n+([\s\S]{500,8000}?)(?=\n\s*(?:results?|experiments?|evaluation|conclusion|discussion))',
            text, re.DOTALL
        )
        if section_match:
            return section_match.group(1)
        return text[:20000]

    def detect_technologies(self, text: str) -> List[str]:
        """Detect technologies and tools used."""
        main_text = re.split(r'(?i)(?:references|bibliography)', text)[0][:40000]
        
        tech_keywords = {
            'Python': ['python', 'pytorch', 'tensorflow', 'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'opencv', 'pillow', 'nltk', 'spacy', 'gensim', 'networkx', 'plotly', 'torch'],
            'R': ['r language', 'rstudio', 'tidyverse', 'ggplot', 'caret', 'tidymodels', 'mlr', 'rstan', 'brms'],
            'JavaScript': ['javascript', 'node.js', 'react', 'vue', 'angular', 'typescript', 'next.js', 'nuxt', 'express', 'd3.js'],
            'Java': ['java', 'spring', 'maven', 'gradle', 'hibernate', 'junit', 'spark', 'hadoop'],
            'C++': ['c++', 'c programming', 'opencv', 'std::'],
            'MATLAB': ['matlab', 'simulink', 'octave'],
            'Go': ['golang', ' go '],
            'Rust': ['rust', 'cargo'],
            'Swift': ['swift', 'ios', 'xcode'],
            'Kotlin': ['kotlin', 'android'],
            'Cloud AWS': ['aws', 'amazon web services', 's3', 'ec2', 'lambda', 'dynamodb', 'rds'],
            'Cloud Azure': ['azure', 'microsoft azure', 'azure ml'],
            'Cloud GCP': ['google cloud', 'gcp', 'google cloud platform', 'bigquery', 'cloud run'],
            'Databases': ['mysql', 'postgresql', 'mongodb', 'redis', 'sqlite', 'oracle', 'sql server', 'cassandra', 'elasticsearch'],
            'MLOps': ['docker', 'kubernetes', 'kubeflow', 'mlflow', 'wandb', 'weights & biases', 'ray', 'apache spark', 'hadoop', 'airflow', 'dagshub'],
            'Web Frameworks': ['flask', 'django', 'fastapi', 'streamlit', 'gradio', 'express', 'rails', '.net', 'asp.net'],
            'APIs': ['rest api', 'restful', 'graphql', 'grpc', 'api', 'openapi', 'swagger'],
            'Deep Learning': ['deep learning', 'neural network', 'cnn', 'rnn', 'lstm', 'gru', 'transformer', 'bert', 'gpt', 'attention', 'encoder', 'decoder'],
            'NLP': ['nlp', 'natural language processing', 'text mining', 'sentiment analysis', 'ner', 'pos tagging', 'word embedding', 'bert', 'gpt'],
            'Computer Vision': ['computer vision', 'object detection', 'yolo', 'faster rcnn', 'semantic segmentation', 'instance segmentation', 'image classification'],
            'IoT': ['iot', 'internet of things', 'arduino', 'raspberry pi', 'esp32', 'sensor'],
            'Blockchain': ['blockchain', 'ethereum', 'bitcoin', 'solidity', 'web3', 'smart contract'],
            'DevOps': ['devops', 'ci/cd', 'jenkins', 'github actions', 'gitlab ci', 'terraform', 'ansible'],
            'Visualization': ['tableau', 'power bi', 'looker', 'plotly', 'd3', 'matplotlib', 'seaborn'],
        }
        
        detected = []
        text_lower = main_text.lower()
        
        for tech, kw_list in tech_keywords.items():
            for kw in kw_list:
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    detected.append(tech)
                    break
        
        return list(set(detected))[:15]

    def extract_title(self, text: str) -> str:
        """Extract paper title."""
        if not text:
            return "Untitled"
        
        lines = text.split('\n')
        
        skip_patterns = ['http', 'doi:', 'email', 'phone', 'abstract', 'introduction', 'figure', 'table']
        
        for line in lines[:20]:
            line = line.strip()
            
            if not line or len(line) < 10:
                continue
            
            if any(pattern in line.lower() for pattern in skip_patterns):
                continue
            
            if line[0].isupper() and len(line) < 250:
                words = line.split()
                if len(words) >= 2:
                    return line
        
        return lines[0].strip() if lines else "Untitled"

    def extract_goal(self, text: str) -> str:
        """Extract research goal/objective."""
        patterns = [
            r'(?i)(?:goal|objective|aim|purpose)[:\s]+([^\n.]{20,500}\.?)',
            r'(?i)(?:this paper|this study|we) (?:aims?|proposes?|presents?|describes?|intend|focuses?|seek to|attempt to) (?:to )?([^\n.]{20,500}\.?)',
            r'(?i)(?:research question|hypothesis)[:\s]+([^\n.]{20,500}\.?)',
            r'(?i)(?:in this paper|this work|this research) (?:we )?(?:propose|present|develop|introduce|suggest) (?:a|an|the)?\s*([^\n.]{20,400}\.?)',
            r'(?i)(?:the goal|our goal|the aim|our aim) (?:of this|of our)? (?:paper|study|research)? (?:is|was)?\s*to\s+([^\n.]{20,400})',
        ]
        
        for pat in patterns:
            m = re.search(pat, text[:15000])
            if m:
                goal = m.group(1).strip()
                if 20 < len(goal) < 500:
                    goal = re.sub(r'^[\'"]|[\'"]$', '', goal)
                    goal = re.sub(r'^\s*[-–—]+\s*', '', goal)
                    if len(goal) > 20:
                        return goal
        
        sections = text.split('\n\n')
        for i, section in enumerate(sections):
            if re.search(r'(?i)introduction', section[:100]):
                if i + 1 < len(sections):
                    first_sent = re.split(r'[.!?]', sections[i+1])[0]
                    if len(first_sent) > 30:
                        return first_sent.strip()
        
        return ""

    def extract_impact(self, text: str) -> str:
        """Extract main contributions/impact with improved detection and inference."""
        text_sample = text[:30000]
        
        # Priority 1: Direct contribution statements
        patterns = [
            r'(?i)(?:contribution|impact|novelty|main result)s?[:\s]+([^\n.]{20,500}\.?)',
            r'(?i)(?:we (?:demonstrate|show)|our results (?:show|demonstrate)|the key contribution|our main finding|our findings (?:demonstrate|show))[:\s]*([^\n.]{20,500}\.?)',
            r'(?i)(?:this (?:paper|work) (?:makes|provides|offers|presents|introduces) (?:a|an|the) (?:novel|new|significant|substantial) (?:contribution|approach|method))([^\n.]{20,500}\.?)',
            r'(?i)(?:the (?:main|primary|key) contribution (?:of this paper|is|includes))[:\s]+([^\n.]{20,500})',
            r'(?i)(?:key contributions include)[:\s]+([^\n.]{20,500})',
            r'(?i)(?:outperform[sd]?|achieve[sd]?|reach(?:es|ed)?|obtain[sd]?) (?:state-of-the-art|a new|sota|new (?:record|best)|(?:an? )?(?:accuracy|performance|f1|score|precision|recall) (?:of|up to))[:\s]+([^\n.]{20,400})',
            r'(?i)(?:improved|enhanced|advances|breakthrough)[:\s]+(?:by |in |with )?([^\n.]{20,300})',
            r'(?i)(?:significantly|remarkably|substantially) (?:improve[ds]|enhance[sd]|outperform[sd])[:\s]+([^\n.]{20,300})',
            r'(?i)(?:experimental results (?:show|demonstrate|indicate)|our findings (?:show|demonstrate|indicate))[:\s]+([^\n.]{20,400})',
            r'(?i)(?:achieves? (?:an? )?(?:accuracy|performance|f1|score) (?:of|up to|over))[:\s]+([^\n.]{20,300})',
            r'(?i)(?:compared to (?:the )?(?:state-of-the-art|baseline|existing|previous|sota))[:\s]+([^\n.]{20,300})',
        ]
        
        for pat in patterns:
            m = re.search(pat, text_sample)
            if m:
                impact = m.group(1).strip()
                if 20 < len(impact) < 600:
                    impact = re.sub(r'^[\'"]|[\'"]$', '', impact)
                    impact = re.sub(r'^\s*[-–—]+\s*', '', impact)
                    impact = re.sub(r'\s+', ' ', impact)
                    if len(impact) > 30:
                        return impact[:500]
        
        # Priority 2: Extract from conclusion/finding sections
        conclusion_area = text_sample.lower()
        if 'conclusion' in conclusion_area or 'results' in conclusion_area:
            for section_start in ['conclusion', 'results and discussion', 'findings']:
                pos = conclusion_area.find(section_start)
                if pos >= 0:
                    section_text = text_sample[pos:pos+3000]
                    sentences = re.split(r'(?<=[.!?])\s+', section_text)
                    impact_keywords = ['improve', 'advance', 'enhance', 'outperform', 'achieve', 'significant', 'novel', 'breakthrough', 'state-of-the-art', 'sota', 'accuracy', 'performance', 'demonstrate', 'contribution', 'result', 'finding', 'effective', 'efficient']
                    
                    impact_phrases = []
                    for sent in sentences:
                        sent_lower = sent.lower()
                        if any(kw in sent_lower for kw in impact_keywords):
                            if 30 < len(sent.strip()) < 400:
                                impact_phrases.append(sent.strip())
                    
                    if impact_phrases:
                        return ' '.join(impact_phrases[:3])[:500]
        
        # Priority 3: Fallback
        sentences = re.split(r'(?<=[.!?])\s+', text_sample[:20000])
        impact_keywords = ['improve', 'advance', 'enhance', 'outperform', 'achieve', 'significant', 'novel', 'breakthrough', 'state-of-the-art', 'sota', 'accuracy', 'performance', 'demonstrate', 'contribution', 'effective', 'efficient', 'first to', 'best', 'highest', 'lowest', 'reduce', 'increase']
        
        impact_phrases = []
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in impact_keywords):
                if 40 < len(sent.strip()) < 350:
                    impact_phrases.append(sent.strip())
        
        if impact_phrases:
            return ' '.join(impact_phrases[:2])[:450]
        
        # Priority 4: If no impact found, infer from paper content
        return self._infer_impact(text)
    
    def _infer_impact(self, text: str) -> str:
        """Infer potential impact based on paper content analysis."""
        text_lower = text.lower()[:30000]
        
        # Extract key components
        keywords = self.extract_keywords(text, top_n=8)
        methodology = self.detect_methodology(text)
        title = self.extract_title(text)
        abstract = self.extract_abstract(text)
        
        impacts = []
        
        # Analyze technical contributions
        has_pretrained = any(w in text_lower for w in ['pre-trained', 'pretrained', 'foundation', 'llm', 'gpt', 'bert', 'transformer'])
        has_architecture = any(w in text_lower for w in ['architecture', 'network', 'model', 'framework', 'system'])
        has_algorithm = any(w in text_lower for w in ['algorithm', 'method', 'approach', 'technique'])
        has_data = any(w in text_lower for w in ['dataset', 'corpus', 'data', 'training', 'benchmark'])
        has_application = any(w in text_lower for w in ['application', 'use case', 'scenario', 'domain', 'industry'])
        
        # Generate impact statements based on what's in the paper
        if title:
            impacts.append(f"This research presents a novel approach in the field of {title[:50]}...")
        
        if keywords:
            kw_list = ', '.join(keywords[:5])
            impacts.append(f"Potential impact on advancing research in {kw_list} through innovative methodologies")
        
        if methodology:
            methods = ', '.join(methodology[:3])
            impacts.append(f"Development of {methods} techniques that could influence future research directions")
        
        if has_pretrained:
            impacts.append("Contribution to advancing pre-trained model capabilities and fine-tuning strategies")
        
        if has_architecture:
            impacts.append("Introduction of new architectural designs that could improve system performance")
        
        if has_algorithm:
            impacts.append("Development of novel algorithmic approaches with potential for widespread adoption")
        
        if has_data:
            impacts.append("Creation or analysis of datasets that could benefit the research community")
        
        if has_application:
            impacts.append("Potential for practical applications in real-world scenarios and industry settings")
        
        # Add domain-specific impacts
        if any(w in text_lower for w in ['medical', 'health', 'clinical', 'patient', 'diagnosis']):
            impacts.append("Potential for significant impact on healthcare and medical diagnostics")
        
        if any(w in text_lower for w in ['climate', 'environment', 'sustainable', 'energy']):
            impacts.append("Contribution to environmental sustainability and climate change mitigation")
        
        if any(w in text_lower for w in ['education', 'learning', 'student', 'teacher']):
            impacts.append("Potential to transform educational practices and learning outcomes")
        
        if any(w in text_lower for w in ['security', 'cyber', 'attack', 'defense']):
            impacts.append("Advancement in cybersecurity and threat detection capabilities")
        
        if not impacts:
            impacts.append("Contribution to advancing knowledge in the specified research domain")
        
        return ' '.join(impacts[:2])[:450]

    def extract_methodology_summary(self, text: str) -> str:
        """Extract methodology description."""
        patterns = [
            r'(?i)(?:^|\n)\s*(?:methodology|methods|approach)\s*[:.-]*\s*\n+([\s\S]{100,2000}?)(?=\n\s*\n|\n(?=results|experiments|evaluation))',
            r'(?i)(?:^|\n)\s*methods\s*\n-+\n([\s\S]{100,2000}?)(?=\n\s*\n)',
        ]
        
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                summary = m.group(1).strip()
                summary = re.sub(r'\s+', ' ', summary)
                if len(summary) > 50:
                    return summary[:2000]
        return ""

    def detect_research_gaps(self, text: str) -> List[str]:
        """Identify research gaps - both explicit and inferred from paper content."""
        gaps = []
        
        # First, try to find explicit mentions of gaps in the text
        # More comprehensive patterns with better capture
        patterns = [
            # Direct gap mentions
            r'(?i)(?:research\s+)?gap[s]?\s*(?:in|of|found|identified)?\s*(?:in|is|are|remain)?\s*:?\s*([^\n.]{20,200})',
            r'(?i)(?:major\s+)?limitations?\s*(?:of|include|are|found|identified)?\s*:?\s*([^\n.]{20,200})',
            r'(?i)future\s+work\s*(?:include|recommend|suggest)?\s*:?\s*([^\n.]{20,200})',
            r'(?i)(?:we|this\s+paper)\s+(?:plan|intend|propose)\s+to\s+([^\n.]{20,150})',
            r'(?i)limitations?\s+(?:remain|still|include)\s+([^\n.]{20,150})',
            r'(?i)one\s+(?:limitation|challenge|drawback|issue)\s+(?:is|of)\s+([^\n.]{20,150})',
            r'(?i)despite\s+(?:our|this|the)\s+([^\n.]{20,150})',
            r'(?i)however\s*,?\s*(?:this|there|the|our|we)\s+([^\n.]{20,150})',
            r'(?i)although\s+(?:this|there|the|our|we)\s+([^\n.]{20,150})',
            r'(?i)challenge[s]?\s+(?:is|remain|include)\s+([^\n.]{20,150})',
            r'(?i)need[s]?\s+(?:more|further|additional)\s+([^\n.]{20,150})',
            r'(?i)should\s+be\s+(?:investigated|explored|addressed)\s+([^\n.]{20,150})',
            r'(?i)remains?\s+(?:an\s+)?(?:open|unsolved|unresolved)\s+([^\n.]{20,150})',
            r'(?i)not\s+yet\s+(?:explored|investigated|addressed|studied)\s+([^\n.]{20,150})',
            r'(?i)future\s+research\s+direction[s]?\s*:?\s*([^\n.]{20,200})',
            r'(?i)potential\s+(?:future\s+)?research\s+:?\s*([^\n.]{20,150})',
            r'(?i)opportunities?\s+for\s+further\s+([^\n.]{20,150})',
            r'(?i)more\s+work\s+is\s+needed\s+([^\n.]{20,150})',
            r'(?i)additional\s+research\s+is\s+required\s+([^\n.]{20,150})',
            r'(?i)leaves?\s+room\s+for\s+([^\n.]{20,150})',
            # Open problems
            r'(?i)open\s+problem[s]?\s+:?\s*([^\n.]{20,200})',
            r'(?i)unaddressed\s+issue[s]?\s+:?\s*([^\n.]{20,150})',
            r'(?i)future\s+direction[s]?\s+:?\s*([^\n.]{20,200})',
        ]
        
        for pat in patterns:
            try:
                matches = re.findall(pat, text[:40000])
                for m in matches:
                    gap = m.strip()
                    # Clean up
                    gap = re.sub(r'^(by|through|with|and|or|to|for|in|on)\s+', '', gap, flags=re.IGNORECASE)
                    if len(gap) > 15 and len(gap) < 250:
                        gaps.append(gap)
            except:
                pass
        
        # Remove duplicates and limit
        gaps = list(set(gaps))[:10]
        
        # If no explicit gaps found, infer from paper content analysis
        if not gaps:
            gaps = self._infer_research_gaps(text)
        
        return gaps[:8]
    
    def _infer_research_gaps(self, text: str) -> List[str]:
        """Infer potential research gaps by analyzing the paper content."""
        inferred_gaps = []
        text_lower = text.lower()
        text_sample = text[:40000]
        
        # Extract key information from the paper
        title = self.extract_title(text_sample)
        abstract = self.extract_abstract(text_sample)
        keywords = self.extract_keywords(text_sample, top_n=10)
        methodology = self.detect_methodology(text_sample)
        goal = self.extract_goal(text_sample)
        
        # Analyze what the paper does and doesn't cover
        has_performance = any(w in text_lower for w in ['accuracy', 'performance', 'result', 'evaluation', 'benchmark', 'score', 'f1', 'precision', 'recall'])
        has_dataset = any(w in text_lower for w in ['dataset', 'data', 'training', 'testing', 'benchmark'])
        has_scalability = any(w in text_lower for w in ['scalability', 'large-scale', 'compute', 'resource', 'time', 'complexity', 'efficiency'])
        has_realworld = any(w in text_lower for w in ['real-world', 'practical', 'application', 'deployment', 'industry', 'production'])
        has_robustness = any(w in text_lower for w in ['robust', 'adversarial', 'noise', 'generalization', 'transfer', 'cross-domain'])
        has_comparison = any(w in text_lower for w in ['baseline', 'compare', 'existing', 'state-of-the-art', 'sota', 'prior', 'previous work'])
        has_limitations = any(w in text_lower for w in ['limitation', 'challenge', 'difficulty', 'issue', 'problem'])
        has_ethical = any(w in text_lower for w in ['ethical', 'bias', 'fairness', 'privacy', 'security'])
        has_interpretability = any(w in text_lower for w in ['interpret', 'explain', 'attention', 'feature', 'visualization'])
        
        # Generate gap suggestions based on what's missing
        if not has_performance:
            gap_templates = [
                "Performance evaluation on benchmark datasets needs further investigation",
                "Quantitative comparison with state-of-the-art methods is required",
                "More rigorous performance metrics and analysis could strengthen findings"
            ]
            inferred_gaps.append(gap_templates[0])
        
        if not has_scalability:
            inferred_gaps.append("Scalability to larger datasets or real-world applications remains unexplored")
        
        if not has_robustness:
            inferred_gaps.append("Model robustness to adversarial inputs and noise requires further study")
        
        if not has_realworld:
            inferred_gaps.append("Deployment in real-world scenarios and practical applications needs validation")
        
        if not has_ethical:
            inferred_gaps.append("Ethical considerations, bias mitigation, and fairness require deeper investigation")
        
        if not has_interpretability:
            inferred_gaps.append("Model interpretability and explainability aspects are not addressed")
        
        if not has_comparison:
            inferred_gaps.append("Comprehensive comparison with existing approaches is needed")
        
        # Domain-specific gaps based on keywords
        if keywords:
            keyword_str = ', '.join(keywords[:5])
            inferred_gaps.append(f"Application of {keyword_str} to new domains and problems")
        
        # Methodology-based gaps
        if methodology:
            methods_str = ', '.join(methodology[:3])
            inferred_gaps.append(f"Exploring alternative methodologies to complement {methods_str} approaches")
        
        # Based on goal/aim
        if goal and len(goal) > 10:
            inferred_gaps.append(f"Further investigation towards achieving: {goal[:100]}...")
        
        # Add generic but relevant gaps
        if len(inferred_gaps) < 3:
            additional_gaps = [
                "Cross-domain generalization and transfer learning potential",
                "Resource efficiency and computational cost optimization",
                "Integration with existing systems and frameworks",
                "Long-term effects and longitudinal studies",
                "User feedback and iterative improvement"
            ]
            inferred_gaps.extend(additional_gaps[:3])
        
        return inferred_gaps[:6]

    def extract_datasets(self, text: str) -> Dict[str, Any]:
        """Extract dataset information."""
        text_sample = text[:60000]
        dataset_names = set()
        dataset_links = set()
        dataset_descriptions = []

        known_datasets = {
            'imagenet', 'coco', 'mnist', 'cifar', 'squad', 'glue', 'wikipedia',
            'pubmed', 'arxiv', 'openwebtext', 'bookcorpus', 'laion', 'flickr30k',
            'cityscapes', 'kitti', 'waymo', 'celeba', 'lfw', 'ffhq', 'adult',
            'movielens', 'amazon reviews', 'yelp', 'imdb', 'sst', 'conll', 'ontonotes',
            'snli', 'multinli', 'hellaswag', 'arc', 'gsm8k', 'humaneval', 'common crawl',
            'webtext', 'pile', 'redcaps', 'conceptual captions', 'visual genome',
            'mscoco', 'flickr8k', 'stl10', 'fashion mnist', 'svhn', 'usps', 'emnist',
            'bdd100k', 'nuimages', 'oxford iiit pet', 'stanford cars', 'cub-200',
            'celebahq', 'afhq', 'div2k', 'set5', 'set14', 'bsd100', 'urban100',
            'sintel', 'flyingchairs', 'things', 'coco-stuff', 'ade20k', 'pascal voc',
            'cityscape', 'bdd100k', 'lyft', 'nuscene', 'argoverse', 'wod', 'kitti',
            'europarl', 'multi30k', 'wmt14', 'iwslt', 'wmt16', 'flores', 'ted',
            'ptb', 'wikitext', 'lambada', 'blimp', 'winogrande', 'hendrycks',
            'c4', 'pile', 'redpajama', 'dolma', 'slimpajama', 'fineweb',
            'uci', 'titanic', 'iris', 'breast cancer wisconsin', 'diabetes',
            'housing prices', 'tweet', 'squad v2', 'natural questions', 'triviaqa',
            'boolq', 'record', 'drop', 'personality impressions', 'dialogue',
            'mscoco', 'visual genome', 'textvqa', 'vqa', 'gqa', 'clevr', 'spatial sense',
            'kinetics', 'ucf101', 'hmdb51', 'activitynet', 'charades', 'ava',
            'speechcommands', 'librispeech', 'voxceleb', 'common voice', 'libritts',
            'ImageNet', 'COCO', 'MNIST', 'CIFAR', 'SQuAD', 'GLUE', 'PubMed', 'arXiv',
        }
        
        for name in known_datasets:
            if re.search(r'\b' + re.escape(name) + r'\b', text_sample, re.IGNORECASE):
                dataset_names.add(name.title().replace('Cifar', 'CIFAR').replace('Mnist', 'MNIST').replace('Squad', 'SQuAD').replace('Glue', 'GLUE'))

        name_patterns = [
            r'(?i)(?:dataset|data set|corpus|benchmark)[:\s]+["\']?([A-Z][A-Za-z0-9\-\s]{2,60}?)["\']?',
            r'(?i)(?:we use|we used|using|trained on|evaluated on|tested on)\s+(?:the\s+)?([A-Z][A-Za-z0-9\-\s]+(?:dataset|corpus|benchmark|data))',
            r'(?i)(?:collected|gathered|obtained|downloaded)\s+(?:from|by)\s+([A-Z][A-Za-z0-9\-\s]+)',
        ]
        
        for pat in name_patterns:
            matches = re.findall(pat, text_sample)
            for m in matches:
                clean = str(m).strip()
                if 3 < len(clean) < 80:
                    dataset_names.add(clean)

        url_pattern = r'https?://[^\s<>"\'\)]+'
        all_urls = re.findall(url_pattern, text_sample)
        dataset_keywords = ['dataset', 'data.gov', 'kaggle', 'zenodo', 'figshare', 'github.com', 'huggingface.co/datasets', 'paperswithcode', 'drive.google', '/data', 'download']
        for url in all_urls:
            if any(kw in url.lower() for kw in dataset_keywords):
                dataset_links.add(url.rstrip('.,;:'))

        sentences = re.split(r'[.!?]+', text_sample)
        for sent in sentences:
            for name in dataset_names:
                if name.lower() in sent.lower():
                    desc = sent.strip()
                    if 30 < len(desc) < 500 and desc not in dataset_descriptions:
                        dataset_descriptions.append(desc[:500])
                    break

        return {
            'names': sorted(list(dataset_names))[:15],
            'links': sorted(list(dataset_links))[:15],
            'descriptions': dataset_descriptions[:5]
        }

    def extract_links(self, text: str) -> List[str]:
        """Extract all URLs from the paper including DOI, arxiv, GitHub, etc."""
        url_pattern = r'https?://[^\s<>"\'\)\]]+'
        urls = re.findall(url_pattern, text)
        
        cleaned_urls = []
        seen = set()
        
        for url in urls:
            url = url.rstrip('.,;:)')
            
            # Skip very short URLs
            if len(url) < 15:
                continue
            
            # Process special URLs
            if 'doi.org/10.' in url.lower():
                # Extract DOI number only
                doi = url.replace('https://doi.org/', '').replace('http://doi.org/', '')
                if doi and doi not in seen:
                    seen.add(doi)
                    cleaned_urls.append(f"DOI: {doi}")
                continue
            elif 'arxiv.org/abs' in url.lower():
                arxiv_id = url.replace('https://arxiv.org/abs/', '').replace('http://arxiv.org/abs/', '')
                if arxiv_id and arxiv_id not in seen:
                    seen.add(arxiv_id)
                    cleaned_urls.append(f"arXiv: {arxiv_id}")
                continue
            elif 'arxiv.org/pdf' in url.lower():
                arxiv_id = url.replace('https://arxiv.org/pdf/', '').replace('http://arxiv.org/pdf/', '')
                if arxiv_id and arxiv_id not in seen:
                    seen.add(arxiv_id)
                    cleaned_urls.append(f"arXiv PDF: {arxiv_id}")
                continue
            elif 'github.com' in url.lower():
                # Simplify GitHub URLs
                gh_url = url.replace('https://github.com/', '').replace('http://github.com/', '')
                gh_url = gh_url.rstrip('/')
                if gh_url and gh_url not in seen:
                    seen.add(gh_url)
                    cleaned_urls.append(f"GitHub: {gh_url}")
                continue
            elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
                # Extract video ID
                if 'v=' in url:
                    vid = url.split('v=')[1].split('&')[0]
                elif 'youtu.be/' in url:
                    vid = url.split('youtu.be/')[1].split('?')[0]
                else:
                    vid = url
                if vid and vid not in seen:
                    seen.add(vid)
                    cleaned_urls.append(f"YouTube: {vid}")
                continue
            
            # Regular URLs - avoid duplicates
            if url not in seen:
                seen.add(url)
                cleaned_urls.append(url)
        
        return cleaned_urls[:50]

    def extract_references(self, text: str) -> List[str]:
        """Extract references section with comprehensive patterns."""
        references = []
        text_sample = text
        
        # Find references section - try multiple patterns
        ref_section = ""
        
        # Pattern 1: Standard references header followed by content
        ref_patterns = [
            r'(?i)(?:^|\n)\s*(?:references|bibliography|literature\s+cited|works\s+cited)\s*[:.\-–—]*\s*\n+([\s\S]{500,40000}?)(?=\n\s*\n\s*(?:appendix|acknowledg|author|bio|\Z)|\Z)',
            r'(?i)(?:^|\n)\s*references\s*\n[=\-_]{3,}\n*([\s\S]{500,40000}?)(?=\n\s*\n|\Z)',
            r'(?i)(?:^|\n)\s*(?:references|bibliography)\s*[:.\-]*\s*\n([\s\S]{200,40000}?)(?=\n\n|\Z)',
        ]
        
        for pat in ref_patterns:
            m = re.search(pat, text_sample, re.DOTALL | re.MULTILINE)
            if m:
                ref_section = m.group(1).strip()
                if len(ref_section) > 100:
                    break
        
        # Search last 40% if not found
        if not ref_section or len(ref_section) < 100:
            search_start = int(len(text_sample) * 0.6)
            last_portion = text_sample[search_start:]
            for header in ['references', 'bibliography', 'works cited', 'literature cited']:
                pattern = rf'(?i){header}[.:\s]*\n{{0,3}}'
                m = re.search(pattern, last_portion)
                if m:
                    start_pos = m.start() + search_start
                    ref_section = text_sample[start_pos:start_pos+30000]
                    break
        
        # Also search for reference numbers pattern [1], [2], etc. throughout
        if not ref_section or len(ref_section) < 100:
            # Look for sections with numbered references
            numbered_refs = re.findall(r'\[\d+\]\s+[A-Z]', text_sample[:40000])
            if numbered_refs:
                ref_match = re.search(r'\[\d+\]\s+[A-Z]', text_sample)
                if ref_match:
                    search_start = ref_match.start()
                    ref_section = text_sample[search_start:search_start+25000]
        
        # Parse reference lines
        if ref_section:
            ref_lines = ref_section.split('\n')
        else:
            ref_lines = []
        
        # If no ref section found, try extracting inline citations
        if not ref_section or len(ref_section) < 50:
            # Extract author-year citations like (Smith et al., 2020) or [Smith2020]
            author_year_patterns = []
            
            # Pattern: (Author, Year) or (Author et al., Year)
            auth_year = re.findall(r'\(([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|and\s+[A-Z][a-zA-Z]+))?)[,\s]+(\d{4})\)', text_sample[:50000])
            for author, year in auth_year:
                ref_text = f"{author}, {year}"
                if len(ref_text) > 5:
                    author_year_patterns.append(ref_text)
            
            # Pattern: [1], [2], etc. followed by author
            numbered = re.findall(r'\[\d+\]\s*([A-Z][^.\n]{5,80})', text_sample[:50000])
            for ref in numbered:
                ref = ref.strip()[:100]
                if len(ref) > 10:
                    author_year_patterns.append(ref)
            
            # DOI patterns
            dois = re.findall(r'(doi:?\s*)?(10\.\d{4,}/[^\s\]]+)', text_sample[:50000])
            for prefix, doi in dois:
                ref_text = f"DOI: {doi}"
                if len(ref_text) > 10:
                    author_year_patterns.append(ref_text)
            
            if author_year_patterns:
                # Deduplicate and limit
                seen = set()
                for ref in author_year_patterns:
                    ref_clean = ref.strip()[:150]
                    if ref_clean and ref_clean.lower() not in seen:
                        seen.add(ref_clean.lower())
                        references.append(ref_clean)
                
                if references:
                    return references[:50]
        
        # Parse each reference line
        for line in ref_lines:
            line = line.strip()
            if len(line) < 10:
                continue
            
            # Remove leading markers: [1], 1., 1), -, etc.
            line = re.sub(r'^[\[\(\d\.\)\-\s]+', '', line)
            line = line.strip()
            
            if len(line) < 15:
                continue
            
            # Clean up whitespace
            cleaned = re.sub(r'\s+', ' ', line)
            
            # Skip if it looks like a header or section marker
            if cleaned.lower() in ['references', 'bibliography', 'acknowledgements']:
                continue
            
            # Extract useful reference info
            # Try to find author and year
            author_year = re.search(r'([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|and\s+[A-Z][a-zA-Z]+))?)[,.\s]+(\d{4})', cleaned)
            if author_year:
                ref_text = f"{author_year.group(1)}, {author_year.group(2)}"
                references.append(ref_text)
            elif len(cleaned) > 20:
                # Use full line truncated
                references.append(cleaned[:180])
        
        # Deduplicate while preserving order
        seen = set()
        unique_refs = []
        for ref in references:
            ref_key = ref.lower()[:50]  # Use first 50 chars as key
            if ref_key not in seen and len(ref) > 5:
                seen.add(ref_key)
                unique_refs.append(ref)
        
        return unique_refs[:50] if unique_refs else []

    def extract_visuals(self, text: str) -> Dict[str, Any]:
        """Extract visual elements info with improved accuracy."""
        visuals = {
            'tables': [],
            'figures': [],
            'counts': {
                'figures': 0,
                'tables': 0,
                'charts': 0
            }
        }

        fig_pattern = r'(?i)\b(?:figure|fig\.?)\s+(\d+[a-zA-Z]?(?:\.\d+)?)'
        table_pattern = r'(?i)\b(?:table)\s+(\d+[a-zA-Z]?(?:\.\d+)?)'
        
        fig_matches = re.findall(fig_pattern, text)
        table_matches = re.findall(table_pattern, text)
        
        fig_numbers = set(fig_matches)
        table_numbers = set(table_matches)
        
        visuals['counts']['figures'] = len(fig_numbers)
        visuals['counts']['tables'] = len(table_numbers)
        visuals['counts']['charts'] = len(re.findall(r'(?i)\b(?:graph|chart|plot|diagram)\s+\d+', text))

        for num in fig_numbers:
            visuals['figures'].append({'number': num, 'caption': f'Figure {num}'})

        for num in table_numbers:
            visuals['tables'].append({'number': num, 'caption': f'Table {num}', 'data': None})

        markdown_tables = re.findall(r'(\|.+\|\s*\n\|[-: |]+\|\s*\n(?:\|.+\|\s*\n)+)', text)
        for md_table in markdown_tables:
            visuals['tables'].append({
                'caption': 'Data Table',
                'data': md_table.strip(),
                'format': 'markdown'
            })

        return visuals

    def extract_results_findings(self, text: str) -> str:
        """Extract results and key findings from paper"""
        patterns = [
            r'(?i)(?:results?|findings?|experimental results?)[\s:]*\n+([^\n]*(?:\n(?!(?:conclusion|discussion|references?|limitations?))[^\n]*)*)',
            r'(?i)(?:we (?:found|observed|show|demonstrate|obtained)|experimental outcome)[:\s]+([^\n\.]{50,800})',
            r'(?i)(?:the results (?:show|indicate|suggest|demonstrate))[:\s]+([^\n\.]{50,800})',
            r'(?i)results[:\s]*\n?([^\n]{20,500})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                result = match.group(1).strip()
                result = re.sub(r'\s+', ' ', result)[:800]
                if len(result) > 30:
                    return result
        
        return ""

    def extract_limitations(self, text: str) -> str:
        """Extract limitations from paper"""
        text_sample = text[:40000]
        
        limitations_section = ""
        patterns = [
            r'(?i)(?:^|\n)\s*limitations?\s*[:.\-–—]*\s*\n+([^\n](?:\n(?!(?:conclusion|references?|acknowledgments?|future|work cited|bibliography))[^\n]*)*)',
            r'(?i)(?:^|\n)\s*limitations?\s*[\n\-=]{5,30}\n*([^\n](?:\n(?!(?:conclusion|references?|acknowledgments?|future))[^\n]*)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_sample, re.DOTALL | re.MULTILINE)
            if match:
                limitations_section = match.group(1).strip()
                limitations_section = re.sub(r'\s+', ' ', limitations_section)
                if 30 < len(limitations_section) < 800:
                    return limitations_section[:600]
        
        fallback_patterns = [
            r'(?i)(?:however|nevertheless|despite).{0,200}(?:limitation|weakness)',
            r'(?i)this (?:study|work|research) (?:has|may have) [a-z]+ (?:limitation|drawback)',
            r'(?i)one\s+(?:limitation|challenge|drawback|issue)\s+(?:is|of)\s+([^\n.]{20,150})',
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, text_sample, re.DOTALL)
            if match:
                limitation = match.group(1).strip() if match.group(1) else match.group(0).strip()
                limitation = re.sub(r'\s+', ' ', limitation)[:600]
                if len(limitation) > 20 and 'reference' not in limitation.lower():
                    return limitation
        
        return ""

    def extract_dataset_details(self, text: str) -> Dict[str, Any]:
        """Extract dataset name, size, and source"""
        dataset_info = {
            'names': [],
            'size': '',
            'source': ''
        }
        
        name_patterns = [
            r'(?i)(?:dataset|data set|corpus|benchmark)[\s:]+([A-Z][a-zA-Z\s]+?)(?:\s+(?:with|from|containing|consists|size|has)|[\.,\n]|$)',
            r'(?i)(?:we (?:used|employed|collected)|using)[\s:]+([A-Z][a-zA-Z\s]+?)(?:\s+dataset|data set)',
            r'(?i)(?:called|named)[\s:]+([A-Z][a-zA-Z\s]+)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if 3 < len(name) < 80:
                    dataset_info['names'].append(name)
        
        size_patterns = [
            r'(\d+(?:,\d+)?)\s*(?:samples?|instances?|records?|images?|videos?|data points?)',
            r'(?i)(?:size|contains?)[:\s]+(\d+(?:,\d+)?(?:\s*(?:K|M|B|k|m|b|thousand|million|billion))?)',
            r'(\d+(?:,\d+)?)\s*(?:GB|MB|KB|GB|TB)',
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, text)
            if match:
                dataset_info['size'] = match.group(0).strip()
                break
        
        source_patterns = [
            r'(?i)(?:source|from|obtained from|collected from)[:\s]+([^\n\.,]{10,100})',
            r'(?i)(?:available at|from)[\s:]+(https?://[^\s]+)',
            r'(?i)(?:public|open[- ]source|benchmark)[\s:]+([^\n\.,]{10,80})',
        ]
        
        for pattern in source_patterns:
            match = re.search(pattern, text)
            if match:
                dataset_info['source'] = match.group(1).strip()
                break
        
        return dataset_info

    def extract_methodology_details(self, text: str) -> Dict[str, Any]:
        """Extract methodology - algorithms and models used"""
        method_info = {
            'algorithms': [],
            'models': [],
            'approach': ''
        }
        
        algo_patterns = [
            r'\b(gradient descent|backpropagation|random forest|svm|support vector machine|k-means|knn|k-nearest neighbor|naive bayes|decision tree|xgboost|catboost|adaboost|k-means|em algorithm)\b',
            r'\b(PCA|SVM|KNN|Naive Bayes|Decision Tree|Random Forest|AdaBoost|XGBoost|CatBoost|Logistic Regression|Linear Regression|K-Means|Hierarchical Clustering)\b',
            r'(?i)(?:algorithm|method)[:\s]+([A-Z][a-zA-Z\s]+?)(?:\s+algorithm|\s+method|[\.,\n]|$)',
        ]
        
        for pattern in algo_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) > 2:
                    method_info['algorithms'].append(match.strip())
        
        model_patterns = [
            r'\b(CNN|ConvNet|ResNet|VGG|Inception|YOLO|R-CNN|Faster R-CNN|Mask R-CNN)\b',
            r'\b(LSTM|GRU|RNN|BiLSTM|Transformer|BERT|GPT|T5|ViT|ChatGPT)\b',
            r'\b(VAE|GAN|Autoencoder|Encoder-Decoder|Sequence-to-Sequence)\b',
            r'(?i)(?:model|architecture)[:\s]+([A-Z][a-zA-Z0-9\s]+?)(?:\s+model|[\.,\n]|$)',
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) > 2:
                    method_info['models'].append(match.strip())
        
        approach_patterns = [
            r'(?i)(?:proposed|our)[\s:]+(?:approach|method|framework|architecture)[:\s]+([^\n\.]{20,150})',
            r'(?i)we (?:propose|develop|design|present)[:\s]+([^\n\.]{20,150})',
            r'(?i)(?:approach|methodology)[:\s]+([^\n\.]{20,150})',
        ]
        
        for pattern in approach_patterns:
            match = re.search(pattern, text)
            if match:
                method_info['approach'] = match.group(1).strip()[:200]
                break
        
        method_info['algorithms'] = list(set(method_info['algorithms']))[:10]
        method_info['models'] = list(set(method_info['models']))[:10]
        
        return method_info

    def calculate_statistics(self, text: str) -> Dict[str, Any]:
        """Calculate text statistics."""
        word_count = len(text.split())
        unique_words = len(set(w.lower() for w in re.findall(r'\b\w+\b', text)))
        sentence_count = len(re.split(r'[.!?]+', text))
        
        return {
            'word_count': word_count,
            'unique_words': unique_words,
            'sentence_count': max(1, sentence_count - 1),
            'avg_words_per_sentence': round(word_count / max(1, sentence_count - 1), 2),
            'characters': len(text),
            'paragraphs': len(re.split(r'\n\s*\n', text))
        }

    def generate_summary(self, text: str, max_length: int = 500, min_length: int = 150) -> str:
        """Generate summary using extractive method with TF-IDF scoring."""
        self._load_models()
        
        if not text or len(text.strip()) < 100:
            return text
        
        return self._extractive_summary(text, max_length)

    def _extractive_summary(self, text: str, max_length: int = 500) -> str:
        """Extractive summary using sentence scoring with optional TF-IDF weighting."""
        if len(text) > 15000:
            text = text[:15000]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        if len(sentences) <= 2:
            return text[:500] if len(text) > 500 else text
        
        stop_words = self._get_stop_words()
        
        # Find position of key sections to prioritize
        abstract_pos = -1
        intro_pos = -1
        conclusion_pos = -1
        
        text_lower = text.lower()
        if 'abstract' in text_lower:
            abstract_pos = text_lower.find('abstract')
        if 'introduction' in text_lower:
            intro_pos = text_lower.find('introduction')
        if 'conclusion' in text_lower:
            conclusion_pos = text_lower.find('conclusion')
        
        important_words = [
            'propose', 'present', 'demonstrate', 'show', 'result', 'method', 'approach', 
            'novel', 'new', 'significant', 'achieve', 'performance', 'accuracy', 'improve',
            'outperform', 'effective', 'efficient', 'experimental', 'evaluation', 'findings',
            'contribution', 'impact', 'conclusion', 'summary', 'study', 'research', 'paper'
        ]
        
        if SKLEARN_AVAILABLE and NLTK_AVAILABLE:
            try:
                words = word_tokenize(text.lower())
                words = [w for w in words if w.isalnum() and w not in stop_words]
                word_freq = Counter(words)
                
                sentence_scores = {}
                for i, sent in enumerate(sentences):
                    sent_words = word_tokenize(sent.lower())
                    score = sum(word_freq.get(w, 0) for w in sent_words)
                    
                    # Position scoring - prioritize sentences from key sections
                    sent_start = text_lower.find(sent.lower()[:50]) if sent else -1
                    if sent_start >= 0:
                        if abstract_pos >= 0 and abstract_pos <= sent_start < abstract_pos + 500:
                            score += 5
                        elif intro_pos >= 0 and intro_pos <= sent_start < intro_pos + 1000:
                            score += 3
                        elif conclusion_pos >= 0 and conclusion_pos <= sent_start < conclusion_pos + 500:
                            score += 4
                    
                    # First few sentences get higher scores
                    if i < 3:
                        score += 4
                    elif i < 6:
                        score += 2
                    
                    # Bonus for important words
                    sent_lower = sent.lower()
                    for word in important_words:
                        if word in sent_lower:
                            score += 1.5
                    
                    # Longer sentences often more informative
                    if len(sent) > 80:
                        score += 1
                    if len(sent) > 150:
                        score += 1
                    
                    sentence_scores[i] = score
                
                # Get more sentences for longer summary
                top_n = min(6, len(sentences))
                top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
                top_sentences = sorted(top_sentences, key=lambda x: x[0])
                summary = ' '.join(sentences[i] for i, _ in top_sentences)
                
                return summary[:max_length].rsplit(' ', 1)[0] + '.' if summary else text[:max_length]
            except Exception as e:
                logger.warning(f"Extractive summary with NLTK failed: {e}")
        
        return self._basic_summary(text, max_length)

    def _basic_summary(self, text: str, max_length: int = 150) -> str:
        """Basic extractive summary without NLTK."""
        if len(text) > 15000:
            text = text[:15000]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        if len(sentences) <= 2:
            return text[:500] if len(text) > 500 else text
        
        scored = []
        for i, sent in enumerate(sentences):
            score = 0
            if i < 3:
                score += 3
            elif i < 5:
                score += 1
            
            important_words = ['propose', 'present', 'demonstrate', 'show', 'result', 'method', 'approach', 'novel', 'new', 'significant', 'achieve', 'performance', 'accuracy']
            sent_lower = sent.lower()
            for word in important_words:
                if word in sent_lower:
                    score += 1
            
            if len(sent) > 80:
                score += 1
            
            scored.append((score, sent))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s[1] for s in scored[:4]]
        
        top_sentences.sort(key=lambda x: sentences.index(x))
        
        return ' '.join(top_sentences[:3])[:max_length]

    def detect_paper_standard(self, text: str) -> str:
        """Detect paper standard (IEEE, ACM, APA, etc.)"""
        text_lower = text.lower()
        
        standards = {
            'IEEE': ['ieee', 'conference on', 'transactions on', ' ieee '],
            'ACM': ['acm', 'association for computing machinery', 'sigchi', 'sigmod'],
            'APA': ['apa style', 'american psychological association', 'doi:', '10.'],
            'MLA': ['mla style', 'modern language association'],
            'Chicago': ['chicago style', 'chicago manual of style'],
            'Harvard': ['harvard style', 'harvard reference'],
            'Nature': ['nature', 'nature publishing'],
            'Science': ['science', 'sciencemag'],
            'Elsevier': ['elsevier', 'procedia', 'journal of'],
            'Springer': ['springer', 'lecture notes', 'computer science']
        }
        
        for standard, keywords in standards.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return standard
        
        return "Academic Standard"

    def full_analysis(self, text: str) -> Dict:
        """Perform full analysis on text."""
        self._load_models()

        max_chars = int(os.getenv("ANALYSIS_TEXT_MAX", "52000"))
        if text and len(text) > max_chars:
            text = text[:max_chars]

        abstract = self.extract_abstract(text)
        native_summary = self.extract_native_summary(text)
        conclusion = self.extract_conclusion(text)
        dataset_info = self.extract_datasets(text)
        visuals = self.extract_visuals(text)
        title = self.extract_title(text)

        return {
            'title': title,
            'authors': self.extract_authors(text),
            'publication_year': self.extract_publication_year(text),
            'abstract': abstract,
            'summary': self.generate_summary(text[:5000]) if abstract else native_summary,
            'native_summary': native_summary,
            'conclusion': conclusion,
            'keywords': self.extract_keywords(text),
            'methodology': self.detect_methodology(text),
            'methodology_summary': self.extract_methodology_summary(text),
            'technologies': self.detect_technologies(text),
            'goal': self.extract_goal(text),
            'impact': self.extract_impact(text),
            'research_gaps': self.detect_research_gaps(text),
            'dataset_names': dataset_info.get('names', []),
            'dataset_links': dataset_info.get('links', []),
            'dataset_section': '\n'.join(dataset_info.get('descriptions', [])),
            'visual_assets': visuals,
            'extracted_links': self.extract_links(text),
            'references': self.extract_references(text),
            'statistics': self.calculate_statistics(text),
        }


ml_processor = MLProcessor()
