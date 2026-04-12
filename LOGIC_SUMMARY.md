# Paper Analyzer - Technical Documentation

## Architecture Overview
This is a Django-based research paper analysis web application that extracts and analyzes content from PDF files, text input, or URLs.

---

## Technology Stack

### Core Framework
- **Django >= 4.2** - Python web framework
- **djangorestframework** - REST API support

### PDF Processing
- **pdfplumber >= 0.10.3** - Primary PDF extraction (text, tables, images)
- **pypdf >= 3.17.0** - Fallback PDF extraction
- **Pillow** - Image processing
- **pdf2image** - PDF to image conversion

### NLP & Machine Learning
- **nltk >= 3.8.1** - Natural language toolkit (tokenization)
- **scikit-learn >= 1.3.1** - TF-IDF vectorization for keywords/summaries
- **numpy >= 1.24.0** - Numerical operations (supporting sklearn)

### Web & Data
- **beautifulsoup4 >= 4.12.0** - HTML parsing for web scraping
- **requests >= 2.31.0** - HTTP requests
- **lxml >= 4.9.0** - XML/HTML processing

### Export & Utilities
- **reportlab >= 4.0.0** - PDF report generation
- **python-dotenv** - Environment variable management
- **fitz** (PyMuPDF) - PDF processing
- **yt-dlp** - Media downloading

---

## ML Models Used

### ⚠️ NO Heavy Transformer Models
The system uses **extractive methods** only - no BERT, GPT, or other large language models.

#### 1. TF-IDF (scikit-learn)
- **Keyword Extraction**: `TfidfVectorizer` with unigrams and bigrams
- Scores terms by frequency × inverse document frequency
- Falls back to basic frequency analysis if sklearn unavailable

#### 2. Extractive Summarization
- Scores sentences by position (first sentences weighted higher)
- Bonus points for important words (propose, demonstrate, result, etc.)
- Returns top-scored sentences in original order for coherence

#### 3. SequenceMatcher (Python stdlib)
- Character-level similarity for plagiarism detection

#### 4. N-gram Analysis
- 3-gram extraction for text comparison
- Jaccard similarity for overlap calculation

#### 5. Keyword Frequency Analysis
- Stop word filtering
- Most common terms extraction as fallback

---

## Main Logic Flow

### 1. Input Processing (views.py)
```
analyze_document(request)
├── PDF upload → validate_pdf_file() → pdf_processor.extract_text()
├── Text input → direct text analysis
└── URL input → url_scraper.scrape() or local file handling
```

### 2. PDF Extraction (pdf_processor.py)
- **extract_text()**: Uses pdfplumber (primary) or pypdf (fallback)
- **extract_images()**: Extracts embedded images using pdfplumber
- **extract_tables()**: Detects and extracts tables
- **detect_charts()**: Identifies charts/diagrams via keyword search + object detection
- **detect_paper_standard()**: Identifies IEEE, ACM, APA, etc.

### 3. NLP Analysis (ml_model.py - MLProcessor)
The primary NLP module with all extraction methods:
- **extract_title()**: Heuristic-based title extraction (first proper line)
- **extract_abstract()**: Regex patterns for labeled abstract sections
- **extract_keywords()**: TF-IDF (sklearn) with frequency fallback
- **detect_methodology()**: Keyword matching for ML, DL, NLP, CV, etc.
- **detect_technologies()**: Technology detection (Python, AWS, Docker, etc.)
- **extract_goal()**: Research objective extraction
- **extract_impact()**: Contribution/impact extraction
- **detect_research_gaps()**: Identifies limitations and future work
- **extract_datasets()**: Known dataset name matching + URL extraction
- **extract_links()**: URL extraction from text
- **extract_references()**: References section extraction
- **generate_summary()**: Extractive summarization using sentence scoring
- **calculate_statistics()**: Word count, unique words, etc.
- **full_analysis()**: Orchestrates all extraction methods

### 4. Plagiarism Checking (plagiarism.py)
- **local_library_similarity()**: Compares against user's stored documents
- **text_quality_check()**: Detects suspicious patterns
- **extract_key_phrases()**: N-gram phrase extraction
- **comprehensive_plagiarism_check()**: Combined analysis

### 5. Additional Processing (nlp_processor.py - EnhancedNLPProcessor)
Alternative NLP processing - used as secondary fallback:
- TF-IDF-based keyword extraction
- Technology and methodology detection (simpler version)

### 6. Analysis Orchestration (analysis_processor.py)
- Coordinates complete analysis pipeline
- Confidence scoring
- Quality metrics calculation

---

## Key Features

1. **Multi-format Input**: PDF, plain text, URL, local file path
2. **Duplicate Detection**: Prevents re-analyzing same content
3. **Visual Extraction**: Images, tables, charts from PDFs
4. **Plagiarism Detection**: Local library comparison
5. **Paper Comparison**: Side-by-side analysis of two papers
6. **Export Options**: PDF and text export
7. **Email Reports**: Send analysis via email
8. **User Library**: Personal document storage

---

## Database Models

- **Document**: Stores original uploaded content
- **AnalysisResult**: Stores extracted analysis
- **PlagiarismCheck**: Stores similarity scores
- **AnalysisFeedback**: User feedback on accuracy

---

## API Endpoints (views.py)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/` | POST | Analyze document |
| `/result/<id>/` | GET | View analysis result |
| `/library/` | GET | User's document library |
| `/delete/<id>/` | POST | Delete document |
| `/export/<id>/<format>/` | GET | Export analysis |
| `/compare/<id1>/<id2>/` | GET | Compare two papers |
| `/dashboard/` | GET | User dashboard |
| `/profile/` | GET/POST | User profile |

---

## Configuration (Environment Variables)

- `ANALYSIS_TEXT_CAP` - Max characters for analysis (default: 50000)
- `TITLE_SAMPLE_CHARS` - Chars for title extraction (default: 12000)
- `MAX_PDF_UPLOAD_MB` - Max upload size (default: 45MB)
- `MAX_STORE_PDF_MB` - Max storage size (default: 16MB)
- `PDF_MAX_PAGES` - Max PDF pages to process (default: 30)
- `PDF_PREFER_FAST` - Use pypdf before pdfplumber (default: True)
- `ANALYSIS_TEXT_MAX` - Max text for analysis (default: 52000)

---

## Memory Usage

The application is designed to work on systems with 8GB RAM:
- **No large model downloads** - TF-IDF is lightweight
- **Text truncation** - Large documents are truncated before processing
- **Fallback methods** - If sklearn fails, basic frequency analysis is used
- **Efficient n-gram calculation** - Uses Python sets for fast comparison
