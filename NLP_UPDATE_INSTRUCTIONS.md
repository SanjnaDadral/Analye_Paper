# NLP Module Update Instructions

## Files Modified

1. **ml_model.py** - Updated with TF-IDF integration (sklearn) + fallbacks
2. **LOGIC_SUMMARY.md** - Updated documentation
3. **test_nlp.py** - New test script

## Backups Created

- `analyzer/ml_model.py.backup`
- `analyzer/nlp_processor.py.backup`
- `LOGIC_SUMMARY.md.backup`

---

## Setup Instructions

### 1. Verify Requirements

Your `requirements.txt` already includes the necessary packages:

```
Django>=4.2,<5.0
djangorestframework>=3.14.0
pdfplumber>=0.10.3
beautifulsoup4>=4.12.0
requests>=2.31.0
reportlab>=4.0.0
python-dotenv>=1.0.0
scikit-learn>=1.3.1      # ✓ Already present
numpy>=1.24.0             # ✓ Already present
lxml>=4.9.0
bs4>=0.0.1
nltk>=3.8.1              # ✓ Already present
pypdf>=3.17.0
pdf2image>=1.16.3
Pillow>=10.0.0
pytesseract>=0.3.10
fitz>=0.0.1.dev2
yt-dlp>=2023.10.0
```

**No changes needed** - all required packages are already present.

---

### 2. Ensure NLTK Data is Downloaded

NLTK data is downloaded automatically when `ml_model.py` is first imported. However, if you want to ensure it's downloaded beforehand, run:

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

Or in Python:
```python
import nltk
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
```

---

### 3. No Changes to views.py Required

The imports in `views.py` remain unchanged:

```python
from .ml_model import ml_processor
```

The `ml_processor` object has all the same methods:
- `extract_title()`
- `extract_abstract()`
- `extract_keywords()`
- `detect_methodology()`
- `detect_technologies()`
- `generate_summary()`
- `full_analysis()`
- etc.

---

### 4. Run Test Script

To verify everything works:

```bash
cd C:\Users\sanjn\paper\paper_analyzer
python test_nlp.py
```

Expected output:
```
============================================================
NLP MODULE TEST SUITE
============================================================

============================================================
Testing TF-IDF Keyword Extraction
============================================================
Sample text length: 2712 characters
----------------------------------------
Extracted Keywords (0.0023s):
  1. Deep Learning
  2. NLP
  3. Natural Language
  4. Language Processing
  5. Models
  ...

============================================================
Testing Summary Generation
============================================================
...

✓ All tests passed!
```

---

## Rollback Instructions

If anything goes wrong, restore from backups:

```bash
# Restore ml_model.py
copy analyzer\ml_model.py.backup analyzer\ml_model.py

# Restore LOGIC_SUMMARY.md
copy LOGIC_SUMMARY.md.backup LOGIC_SUMMARY.md
```

---

## Key Changes in ml_model.py

1. **TF-IDF Integration**: Uses `sklearn.feature_extraction.text.TfidfVectorizer` for keyword extraction
2. **Fallback Methods**: If sklearn fails, uses basic frequency analysis
3. **NLTK Integration**: Downloads punkt/stopwords automatically
4. **Memory Efficient**: No large models loaded
5. **All Methods Preserved**: Same API as before - no breaking changes
