"""
Enhanced NLP Processor for Research Paper Analysis
Implements: Summarization, Keyword Extraction, Technology Detection, Methodology Extraction
"""

import re
import logging
import os
from typing import Dict, List, Tuple, Any
from collections import Counter
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


class EnhancedNLPProcessor:
    """Advanced NLP processing for research papers"""
    
    def __init__(self):
        self.summarizer = None
        self.models_loaded = False
        self._init_transformers()
        self.stop_words = set(stopwords.words('english'))
        
        # Technology keywords database
        self.tech_keywords = {
            'ML/AI': ['machine learning', 'deep learning', 'neural network', 'lstm', 'cnn', 
                     'transformer', 'bert', 'gpt', 'nlp', 'cv', 'artificial intelligence', 'ai'],
            'Web': ['javascript', 'react', 'vue', 'angular', 'node.js', 'express', 'django', 
                   'flask', 'fastapi', 'rest api', 'graphql', 'websocket'],
            'Data': ['sql', 'mongodb', 'redis', 'elasticsearch', 'hadoop', 'spark', 'kafka',
                    'database', 'bigdata', 'data warehouse', 'etl'],
            'Cloud': ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'ci/cd', 'devops',
                     'microservices', 'serverless', 'cloud computing'],
            'Mobile': ['ios', 'android', 'react native', 'flutter', 'xamarin', 'mobile app'],
            'Security': ['cryptography', 'encryption', 'ssl', 'oauth', 'jwt', 'vulnerability',
                        'penetration testing', 'security']
        }
        
        # Methodology keywords
        self.methodology_keywords = {
            'Experimental': ['experiment', 'empirical', 'evaluation', 'benchmark', 'dataset', 'metric'],
            'Theoretical': ['theorem', 'proof', 'mathematical', 'algorithm', 'complexity', 'analysis'],
            'Simulation': ['simulation', 'model', 'monte carlo', 'agent-based', 'discrete event'],
            'Survey': ['survey', 'review', 'literature', 'systematic', 'meta-analysis'],
            'Case Study': ['case study', 'investigation', 'example', 'real-world'],
            'Mixed Methods': ['mixed methods', 'qualitative', 'quantitative', 'triangulation']
        }

    def _init_transformers(self):
        """Initialize lightweight transformer models for efficient NLP processing"""
        # Use extractive summarization instead of heavy transformer models
        # TF-IDF based extraction is fast and works well for research papers
        self.summarizer = None  # Use fallback extractive method
        logger.info("✓ Lightweight extractive summarization ready")
        self.models_loaded = True

    def extract_title(self, text: str) -> str:
        """Extract paper title with improved heuristics"""
        if not text or len(text) < 20:
            return ""
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # First 5 lines are usually title-related
        for line in lines[:5]:
            if len(line) > 15 and len(line) < 300:
                # Check if it starts with digit (likely abstract number)
                if not re.match(r'^\d+[\.\)]', line):
                    # Check if it looks like a title (ends with period or no lowercase start)
                    if not line[0].islower():
                        return line.strip('.')
        
        # Fallback: first non-empty line that isn't too short
        for line in lines[:10]:
            if len(line) > 20 and len(line) < 300 and line[0].isupper():
                return line.strip('.')
        
        return ""

    def extract_abstract(self, text: str) -> str:
        """Extract abstract section with improved detection"""
        if not text:
            return ""
        
        # Pattern 1: Labeled abstract
        patterns = [
            r'(?i)(?:^|\n)\s*abstract\s*[:.-]*\s*\n+([^\n]*(?:\n(?!(?:keywords?|introduction|background|1\.|2\.|figure|table))[^\n]*)*)',
            r'(?i)(?:^|\n)\s*abstract\s*\n-+\n([\s\S]{100,3000}?)(?=\n\s*\n)',
            r'(?i)<abstract>([\s\S]{100,3000}?)</abstract>',
            r'(?i)(?:^|\n)\s*summary\s*[:.-]*\s*\n+([\s\S]{100,2000}?)(?=\n\s*(?:keywords?|introduction|1\.))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                abstract = re.sub(r'\s+', ' ', abstract)
                if 50 < len(abstract) < 3000:
                    return abstract
        
        # Pattern 2: First substantial paragraph
        paragraphs = re.split(r'\n\s*\n+', text[:10000])
        for para in paragraphs[1:6]:  # Skip title, check next 5 paragraphs
            para = para.strip()
            if 100 < len(para) < 2000:
                # Exclude sections and metadata
                if not re.search(r'(?i)^(introduction|background|related|method|result|conclusion|reference|keyword)', para):
                    if not re.match(r'^\d+\.', para):
                        return para
        
        return ""

    def extract_keywords_tfidf(self, text: str, top_n: int = 10) -> List[str]:
        """Extract keywords using TF-IDF"""
        if not text or len(text) < 100:
            return []
        
        try:
            # Split into sentences
            sentences = sent_tokenize(text[:5000])
            if len(sentences) < 3:
                sentences = text.split('.')
            
            # Use TF-IDF
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.8
            )
            
            texts = [s.strip() for s in sentences if len(s.strip()) > 10]
            if len(texts) < 2:
                texts = text.split('\n')
            
            try:
                matrix = vectorizer.fit_transform(texts)
                scores = matrix.sum(axis=0).A1
                terms = vectorizer.get_feature_names_out()
                top_indices = np.argsort(scores)[-top_n:][::-1]
                keywords = [terms[i] for i in top_indices if scores[i] > 0]
                return keywords[:top_n]
            except:
                return []
                
        except Exception as e:
            logger.warning(f"TF-IDF extraction failed: {e}")
            return []

    def extract_keywords_pattern(self, text: str, top_n: int = 10) -> List[str]:
        """Extract keywords from labeled keyword section"""
        if not text:
            return []
        
        # Look for keywords section
        patterns = [
            r'(?i)keywords?[\s:]*([^\n]+)',
            r'(?i)key terms?[\s:]*([^\n]+)',
            r'(?i)tags?[\s:]*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                kw_text = match.group(1)
                # Split by comma, semicolon, or whitespace
                keywords = re.split(r'[,;]|\s+and\s+', kw_text)
                keywords = [kw.strip() for kw in keywords if kw.strip()]
                return keywords[:top_n]
        
        return []

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extract keywords combining multiple strategies"""
        # First try to find labeled keywords
        keywords = self.extract_keywords_pattern(text, top_n)
        if keywords:
            return keywords
        
        # Fallback to TF-IDF
        return self.extract_keywords_tfidf(text, top_n)

    def generate_summary(self, text: str, max_length: int = 500, min_length: int = 150) -> str:
        """Generate summary using transformers or extractive method"""
        if not text or len(text) < 100:
            return ""
        
        if len(text) > 15000:
            text = text[:15000]
        
        sentences = sent_tokenize(text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        if len(sentences) <= 2:
            return text[:max_length] if len(text) > max_length else text
        
        words = word_tokenize(text.lower())
        words = [w for w in words if w.isalnum() and w not in self.stop_words]
        word_freq = Counter(words)
        
        important_words = [
            'propose', 'present', 'demonstrate', 'show', 'result', 'method', 'approach', 
            'novel', 'new', 'significant', 'achieve', 'performance', 'accuracy', 'improve',
            'outperform', 'effective', 'efficient', 'experimental', 'evaluation', 'findings',
            'conclusion', 'impact', 'study', 'research', 'data', 'analysis', 'conclusion'
        ]
        
        sentence_scores = {}
        for i, sent in enumerate(sentences):
            words_in_sent = word_tokenize(sent.lower())
            score = sum(word_freq.get(w, 0) for w in words_in_sent)
            score += sum(3 for w in words_in_sent if w in important_words)
            
            if i == 0:
                score += 2
            if 'conclusion' in sent.lower() or 'result' in sent.lower():
                score += 2
            
            sentence_scores[i] = score
        
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        top_sentences = sorted(top_sentences, key=lambda x: x[0])
        
        summary = ' '.join(sentences[i] for i, _ in top_sentences)
        
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + '.'
        
        return summary

    def _extractive_summary(self, text: str, max_length: int = 500) -> str:
        """Extract key sentences as summary"""
        try:
            if len(text) > 15000:
                text = text[:15000]
            
            sentences = sent_tokenize(text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
            
            if len(sentences) <= 2:
                return text[:max_length] if len(text) > max_length else text
            
            words = word_tokenize(text.lower())
            words = [w for w in words if w.isalnum() and w not in self.stop_words]
            word_freq = Counter(words)
            
            important_words = [
                'propose', 'present', 'demonstrate', 'show', 'result', 'method', 'approach', 
                'novel', 'new', 'significant', 'achieve', 'performance', 'accuracy', 'improve',
                'outperform', 'effective', 'efficient', 'experimental', 'evaluation', 'findings',
                'conclusion', 'impact', 'study', 'research', 'data', 'analysis'
            ]
            
            sentence_scores = {}
            for i, sent in enumerate(sentences):
                words_in_sent = word_tokenize(sent.lower())
                score = sum(word_freq.get(w, 0) for w in words_in_sent)
                score += sum(3 for w in words_in_sent if w in important_words)
                
                if i == 0:
                    score += 2
                if 'conclusion' in sent.lower() or 'result' in sent.lower():
                    score += 2
                
                sentence_scores[i] = score
            
            top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            top_sentences = sorted(top_sentences, key=lambda x: x[0])
            
            summary = ' '.join(sentences[i] for i, _ in top_sentences)
            
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + '.'
            
            return summary
        except Exception as e:
            logger.warning(f"Extractive summarization failed: {e}")
            return text[:max_length]

    def detect_technologies(self, text: str) -> str:
        """Detect technologies mentioned in paper"""
        text_lower = text.lower()
        found_techs = {}
        
        for category, keywords in self.tech_keywords.items():
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                count = len(re.findall(pattern, text_lower, re.IGNORECASE))
                if count > 0:
                    if category not in found_techs:
                        found_techs[category] = []
                    found_techs[category].append((keyword, count))
        
        # Return top technology
        if found_techs:
            top_category = max(found_techs, key=lambda k: len(found_techs[k]))
            return f"{top_category}: {', '.join([t[0] for t in found_techs[top_category][:3]])}"
        
        return "General Computer Science"

    def detect_methodology(self, text: str) -> str:
        """Detect research methodology"""
        text_lower = text.lower()
        found_methods = {}
        
        for method_type, keywords in self.methodology_keywords.items():
            count = sum(len(re.findall(r'\b' + kw + r'\b', text_lower)) for kw in keywords)
            if count > 0:
                found_methods[method_type] = count
        
        if found_methods:
            top_method = max(found_methods, key=found_methods.get)
            return top_method
        
        # Default based on sections
        if re.search(r'(?i)(?:experiment|evaluation|result)', text):
            return "Experimental"
        elif re.search(r'(?i)(?:theorem|proof|algorithm)', text):
            return "Theoretical"
        
        return "Empirical"

    def extract_authors(self, text: str, top_n: int = 5) -> List[str]:
        """Extract author names"""
        authors = set()
        first_10k = text[:10000]
        
        patterns = [
            r'(?:authors?|by|from|at)\s*[:–—]*\s*([^\n]+)',
            r'^([A-Z][a-z]+(?:\s+(?:[A-Z]\.?|[a-z]+))*(?:\s+[A-Z][a-z]+)+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, first_10k, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                text_chunk = match.group(1).strip()
                # Split potential multiple authors
                potential_authors = re.split(r'[,;]|and|\&', text_chunk)
                for author in potential_authors:
                    author = author.strip()
                    if self._is_valid_name(author):
                        authors.add(author)
        
        return sorted(list(authors))[:top_n]

    def _is_valid_name(self, name: str) -> bool:
        """Validate if text is likely a person name"""
        name = name.strip()
        if not name or len(name) < 3 or len(name) > 60:
            return False
        
        # Should have at least one space (first and last name)
        if ' ' not in name:
            return False
        
        # Should start with uppercase
        if not name[0].isupper():
            return False
        
        # Should not contain special chars except dots and hyphens
        if not re.match(r"^[A-Za-z\s\.\-']+$", name):
            return False
        
        return True

    def extract_year(self, text: str) -> str:
        """Extract publication year"""
        patterns = [
            r'(?i)\b(?:published|accepted|presented|copyright|©)\s*(?:in\s+)?(\d{4})',
            r'(?i)arXiv:\d+\.\d+\s+\[.*?\]\s+(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+)?(\d{4})',
            r'(\d{4})\s*©',
            r'doi:10\.\d+/[^\s]+\s*\((\d{4})\)',
            r'\b(20[0-2]\d|19[89]\d)\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        year_str = [m for m in match if m and m.isdigit() and len(m) == 4]
                        if year_str:
                            year = int(year_str[0])
                            if 1990 <= year <= 2030:
                                return str(year)
                    else:
                        year_str = str(match)
                        if year_str.isdigit() and len(year_str) == 4:
                            year = int(year_str)
                            if 1990 <= year <= 2030:
                                return year_str
        
        return ""

    def detect_dataset_info(self, text: str) -> str:
        """Extract dataset or link information"""
        patterns = [
            r'(?i)(?:dataset|data|corpus|benchmark)[\s:]+([^\n\.]+)',
            r'(?i)available at[\s:]+([^\n]+)',
            r'(?i)github[\s:]+([^\n]+)',
            r'https?://[^\s\)]+',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0].strip()
        
        return ""

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
        patterns = [
            r'(?i)(?:limitations?|drawbacks?|weaknesses?)[:\s]*\n?([^\n]*(?:\n(?!(?:conclusion|references?))[^\n]*)*)',
            r'(?i)(?:however|nevertheless|despite).{0,200}(?:limitation|weakness)',
            r'(?i)this (?:study|work|research) (?:has|may have) [a-z]+ (?:limitation|drawback)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                limitation = match.group(1).strip()
                limitation = re.sub(r'\s+', ' ', limitation)[:600]
                if len(limitation) > 20:
                    return limitation
        
        return ""

    def extract_conclusion(self, text: str) -> str:
        """Extract conclusion section"""
        patterns = [
            r'(?i)(?:conclusions?|summary|concluding remarks?)[\s:]*\n+([^\n]*(?:\n(?!(?:references?|acknowledgments?))[^\n]*)*)',
            r'(?i)in (?:conclusion|summary|summary of|concluding),?\s*([^\n]{30,800})',
            r'(?i)(?:to conclude|overall|ultimately)[:\s]+([^\n]{30,800})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                conclusion = match.group(1).strip()
                conclusion = re.sub(r'\s+', ' ', conclusion)[:800]
                if len(conclusion) > 30:
                    return conclusion
        
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


# Global processor instance
nlp_processor = EnhancedNLPProcessor()
