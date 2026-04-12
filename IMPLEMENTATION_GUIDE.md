# PaperAIzer - Backend Implementation Guide

## 🎯 Complete Pipeline Overview

```
User Upload → Validation → PDF Extraction → Text Cleaning → NLP Processing → Database Save → JSON Response
     ↓              ↓              ↓               ↓               ↓              ↓             ↓
  Form      File Check    pdfplumber    Regex + NLTK   Transformers   Document Model   API Response
           Size Limit     Extract Text   Remove Noise   Summarization   + Analysis       + Redirect
```

---

## 📦 Architecture Components

### 1. **PDF Extraction Layer** (`pdf_processor.py`)

- **Purpose:** Extract text and assets from PDF files
- **Methods:**
  - `extract_text()` - Main text extraction using pdfplumber/pypdf
  - `extract_images()` - Pull images from PDF
  - `extract_tables()` - Detect table structures
  - `detect_charts()` - Identify charts/diagrams
  - `detect_paper_standard()` - Identify IEEE/ACM/APA format

**Key Features:**

- Fallback extraction (PyPDF → pdfplumber)
- Page limiting for large PDFs
- Handles corrupted PDFs gracefully
- Returns structured metadata (pages, images, etc.)

### 2. **NLP Processing Layer** (`nlp_processor.py` - NEW)

- **Purpose:** Advanced text analysis using transformers and traditional NLP
- **Key Classes:** `EnhancedNLPProcessor`
- **Methods:**
  - `extract_title()` - Smart title detection
  - `extract_abstract()` - Abstract section extraction
  - `extract_keywords_tfidf()` - TF-IDF keyword extraction
  - `generate_summary()` - BART/DistilBART summarization
  - `detect_technologies()` - Tech stack identification
  - `detect_methodology()` - Research method detection
  - `extract_authors()` - Author name extraction
  - `extract_year()` - Publication year detection

**Output Examples:**

- Keywords: `['Machine Learning', 'Neural Networks', 'Deep Learning']`
- Technologies: `'ML/AI: machine learning, deep learning, neural network'`
- Methodology: `'Experimental'` or `'Theoretical'`

### 3. **Analysis Orchestration** (`analysis_processor.py` - NEW)

- **Purpose:** Coordinate complete analysis pipeline
- **Class:** `AnalysisProcessor`
- **Main Method:** `analyze_document(content, input_type)`
- **Outputs:**
  - Metadata (title, authors, year)
  - Analysis (abstract, summary, keywords)
  - Technical (technologies, methodology)
  - Quality metrics (confidence, completeness)

### 4. **Response Building** (`response_builder.py` - NEW)

- **Purpose:** Structure and validate API responses
- **Class:** `AnalysisResponseBuilder`
- **Methods:**
  - `build_success_response()` - Structured analysis response
  - `build_error_response()` - Standardized error format
  - `validate_analysis_data()` - Ensure required fields
  - `enrich_analysis_data()` - Add metadata and assets

---

## 🚀 Complete Analysis Pipeline

###Step 1: File Upload & Validation

```python
# Location: views.py - analyze_document() function
# Input: File upload via multipart/form-data

# Validation checks:
- File type: Only .pdf allowed
- File size: Max 45MB for upload, 16MB for storage
- File content: Min 1KB, max 50KB for analysis

# Output:
- Validated file object
- File info (size, pages, images)
```

### Step 2: Text Extraction

```python
# Location: pdf_processor.py
from analyzer.pdf_processor import pdf_processor

result = pdf_processor.extract_text(uploaded_file)
# Returns:
# {
#     'success': True,
#     'text': 'Extracted text...',
#     'pages': 25,
#     'embedded_image_objects': 3,
#     'pages_extracted': 25
# }

text = result.get('text', '')[:50000]  # Cap at 50K chars
```

### Step 3: NLP Analysis (NEW - Enhanced)

```python
# Location: analyzer/ml_model.py - full_analysis()
from analyzer.ml_model import ml_processor

analysis_data = ml_processor.full_analysis(text)
# Returns comprehensive dict:
# {
#     'title': 'Paper Title',
#     'abstract': 'Full abstract...',
#     'summary': 'AI-generated summary',
#     'keywords': ['term1', 'term2', ...],
#     'authors': ['Author Name', ...],
#     'publication_year': '2024',
#     'technologies': ['Python', 'TensorFlow'],
#     'methodology': ['Machine Learning', 'Experimental'],
#     'goal': 'Research objective...',
#     'impact': 'Main contributions...',
#     'dataset_names': ['Dataset1'],
#     'dataset_links': ['http://...'],
#     'references': ['Ref1'],
#     'statistics': {
#         'word_count': 5000,
#         'unique_words': 800
#     }
# }
```

### Step 4: Plagiarism Check

```python
# Location: plagiarism.py
from analyzer.plagiarism import local_library_similarity

plagiarism_result = local_library_similarity(document_id, text)
# Returns:
# {
#     'similarity_percent': 15.5,
#     'matches': [{doc_id, title, similarity}],
#     'risk_level': 'low'  # low/medium/high
# }
```

### Step 5: Store in Database

```python
# Create Document record
document = Document.objects.create(
    user=request.user,
    input_type='pdf',
    title=title,
    content=text,
    file=file,
    word_count=len(text.split())
)

# Create AnalysisResult record
analysis_result = AnalysisResult.objects.create(
    document=document,
    summary=analysis_data['summary'],
    keywords=analysis_data['keywords'],
    technologies=analysis_data['technologies'],
    # ... all fields
)

# Create PlagiarismCheck record
PlagiarismCheck.objects.create(
    document=document,
    similarity_score=plagiarism_result['similarity_percent'] / 100,
    matched_sources=plagiarism_result['matches']
)
```

### Step 6: Return Structured Response

```python
# Location: views.py
response = {
    'success': True,
    'analysis': {
        'id': analysis_result.id,
        'title': document.title,
        'metadata': {
            'authors': [...],
            'year': '2024',
            'word_count': 5000
        },
        'content': {
            'abstract': '...',
            'summary': '...',
            'keywords': [...]
        },
        'technical': {
            'technologies': [...],
            'methodology': [...]
        },
        'plagiarism': {...},
        'assets': {
            'extracted_images': [...],
            'extracted_tables': [...]
        }
    },
    'redirect_url': '/result/123/'
}

return JsonResponse(response)
```

---

## 🎨 Frontend Integration

### JavaScript Handler: `analysis_handler.js`

Located at: `static/js/analysis_handler.js`

**Features:**

- Form validation (file type, size, content length)
- Drag-and-drop file upload
- Real-time progress bar (10% → 100%)
- Error handling with user-friendly messages
- Success feedback with quick stats
- Loading spinner during processing

**Usage:**

```html
<!-- In upload.html template -->
<script src="{% static 'js/analysis_handler.js' %}"></script>

<!-- Handler automatically initializes on page load -->
<!-- Manages:
    - Tab switching (PDF/Text/URL)
    - Form submission via AJAX
    - Progress updates
    - Error display
    - Redirect on success
-->
```

### Form Elements Required:

```html
<form id="analysisForm">
  <!-- Method tabs -->
  <button class="method-tab active" data-method="pdf">PDF</button>
  <button class="method-tab" data-method="text">Text</button>
  <button class="method-tab" data-method="url">URL</button>

  <!-- PDF input -->
  <input id="pdfFile" type="file" accept=".pdf" data-method="pdf" />

  <!-- Text input -->
  <textarea id="textContent" data-method="text"></textarea>

  <!-- URL input -->
  <input id="urlInput" type="url" data-method="url" />

  <!-- Submit button -->
  <button id="submitBtn" type="submit">Analyze Paper</button>

  <!-- Progress container (auto-created) -->
  <div id="progressContainer"></div>
</form>
```

---

## 🔧 Configuration & Environment Variables

```env
# ML Model Configuration
ENABLE_HEAVY_ML=True                    # Use BART/KeyBERT models
ANALYSIS_TEXT_CAP=50000                 # Max chars for analysis

# PDF Processing
PDF_MAX_PAGES=30                        # Skip pages beyond this
PDF_PREFER_FAST=True                    # Use PyPDF first
LARGE_PDF_SKIP_PLUMBER_MB=12           # Skip pdfplumber for large PDFs

# File Size Limits
MAX_PDF_UPLOAD_MB=45                    # Max upload size
MAX_STORE_PDF_MB=16                     # Max storage size

# Database
DATABASE_URL=sqlite:///db.sqlite3       # Default Django DB
```

---

## 📊 Data Models

### Document Model

```python
class Document(models.Model):
    user = ForeignKey(User)
    input_type = CharField('pdf'/'text'/'url')
    title = CharField(max_length=500)
    content = TextField()  # Full extracted text
    file = FileField(null=True)  # Original PDF
    url = URLField(null=True)  # Source URL
    word_count = IntegerField()
    created_at = DateTimeField(auto_now_add=True)
```

### AnalysisResult Model

```python
class AnalysisResult(models.Model):
    document = OneToOneField(Document)
    abstract = TextField()
    summary = TextField()
    keywords = JSONField()  # List of keywords
    authors = JSONField()  # List of author names
    technologies = JSONField()  # List of tech stacks
    methodology = JSONField()  # List of methods
    references = JSONField()  # List of references
    dataset_names = JSONField()
    dataset_links = JSONField()
    extracted_links = JSONField()
    goal = TextField()
    impact = TextField()
    publication_year = CharField()
    word_count = IntegerField()
    unique_words = IntegerField()
    extras = JSONField()  # Additional metadata
```

---

## ✅ Testing the Pipeline

### Test 1: PDF Upload

```bash
curl -X POST http://localhost:8000/analyze/ \
  -F "input_type=pdf" \
  -F "pdf_file=@sample_paper.pdf" \
  -H "Cookie: csrftoken=YOUR_TOKEN"
```

### Test 2: Text Input

```bash
curl -X POST http://localhost:8000/analyze/ \
  -d "input_type=text&text_content=Your+text+content+here..." \
  -H "Cookie: csrftoken=YOUR_TOKEN"
```

### Expected Response:

```json
{
  "success": true,
  "analysis": {
    "title": "Paper Title",
    "metadata": {
      "authors": ["Author Name"],
      "year": "2024",
      "word_count": 5000
    },
    "content": {
      "abstract": "...",
      "summary": "...",
      "keywords": ["AI", "ML", "Deep Learning"]
    },
    "technical": {
      "technologies": ["Python", "TensorFlow"],
      "methodology": ["Experimental"]
    }
  },
  "redirect_url": "/result/123/"
}
```

---

## 🐛 Error Handling

### Common Errors & Fixes

| Error                 | Cause                   | Solution                            |
| --------------------- | ----------------------- | ----------------------------------- |
| `File too large`      | PDF > 45MB              | Split PDF or use smaller file       |
| `No extractable text` | Scanned PDF             | Try OCR or upload text version      |
| `Duplicate paper`     | Same content uploaded   | Check library or modify pdf         |
| `Analysis incomplete` | Low quality extraction  | Manually review abstract/keywords   |
| `No models loaded`    | ENABLE_HEAVY_ML not set | Set env var or use lightweight mode |

---

## 📈 Performance Optimization

### Current Benchmarks:

- PDF Extraction: ~2-5 seconds
- NLP Analysis: ~3-8 seconds (with transformers)
- Database Save: ~0.5 seconds
- **Total:** ~5-15 seconds per paper

### Optimization Tips:

1. **Use lightweight mode for CPU-only servers** (removes BART)
2. **Batch process multiple papers** (use async tasks)
3. **Cache extracted features** in Redis
4. **Limit PDF pages** (PDF_MAX_PAGES=30)
5. **Use CDN for static assets** (JS, CSS)

---

## 🔐 Security Considerations

✅ **Implemented:**

- CSRF protection on all forms
- File type validation (PDF only)
- File size limits
- SQL injection prevention (Django ORM)
- User authentication required

⚠️ **Recommendations:**

- Add rate limiting on /analyze/ endpoint
- Sanitize extracted text before display
- Validate regex patterns for injection
- Use environment variables for secrets
- Enable HTTPS in production

---

## 📝 Dependencies & Installation

```bash
# Install all requirements
pip install -r requirements.txt

# Download NLP models (one-time)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

---

## 🎯 Next Steps & Enhancements

1. **Async Processing** - Use Celery for background analysis
2. **OCR Support** - Handle scanned PDFs with Tesseract
3. **Citation Recognition** - Extract and format references
4. **Dataset Detection** - Link to external datasets
5. **Visualization** - Generate charts from data
6. **Plagiarism GUI** - Show matched sections
7. **Multi-language Support** - Translate abstracts
8. **API Endpoints** - RESTful API for programmatic access

---

## 📞 Support

For issues or questions:

1. Check environment variables
2. Review logs: `tail -f logs/django.log`
3. Test extraction: `python manage.py shell` → `from analyzer.pdf_processor import pdf_processor`
4. Verify models: `python manage.py shell` → `from analyzer.nlp_processor import nlp_processor`
