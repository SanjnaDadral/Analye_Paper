# 🧪 Quick Testing Guide - PaperAIzer

## Pre-Test Checklist

- [ ] Python 3.13+ installed
- [ ] Virtual environment activated
- [ ] `requirements.txt` installed
- [ ] `python manage.py migrate` completed
- [ ] NLTK models downloaded
- [ ] Test PDF prepared

## Step-by-Step Testing

### Test 1: Start Server ✅

```bash
cd c:\Users\sanjn\paper\paper_analyzer
python manage.py runserver 0.0.0.0:8000
```

**Expected Output:**

```
Django version 6.0.3, using settings 'paper_analyzer.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

**✓ If server starts without errors, PDF extraction layer is ready**

---

### Test 2: Website Access 🌐

Navigate to: `http://localhost:8000/`

**Expected:**

- [ ] Hero section loads with side-by-side layout
- [ ] 6 colorful feature cards visible
- [ ] "How It Works" section with 4 rainbow icons
- [ ] No console errors (F12 → Console tab)

**✓ If homepage loads, frontend is working**

---

### Test 3: PDF Upload Form 📝

Click "New Analysis" and navigate to upload page

**Expected:**

- [ ] 3 tabs visible: PDF / Paste Text / URL
- [ ] Drag-and-drop zone active
- [ ] File info displays after selection
- [ ] Submit button enabled

**✓ If form loads, upload interface is ready**

---

### Test 4: PDF Analysis (Main Test) 🎯

#### Option A: Test with Sample PDF

1. Have a research paper PDF ready
2. Upload via form
3. Wait for analysis (6-15 seconds)

#### Option B: Test with Text

1. Copy paper abstract or text (>50 chars)
2. Select "Paste Text" tab
3. Submit

#### Expected Response:

```
✓ Progress bar appears (0% → 100%)
✓ Status updates show: "Preparing..." → "Processing..." → "Analyzing..."
✓ Success message with quick stats
✓ Redirects to /result/123/
```

**Result Page Should Show:**

- [ ] Paper title extracted
- [ ] Real keywords (not generic)
- [ ] AI-generated summary (contextual)
- [ ] Detected technologies
- [ ] Methodology identified
- [ ] Quality metrics displayed
- [ ] Recently extracted images/tables

**✓ If analysis completes and displays real data, core pipeline works**

---

### Test 5: Check Database 💾

```bash
python manage.py shell
```

```python
from analyzer.models import Document, AnalysisResult

# Check latest document
doc = Document.objects.last()
print(f"Title: {doc.title}")
print(f"Word Count: {doc.word_count}")

# Check analysis
analysis = doc.analysis
print(f"Keywords: {analysis.keywords}")
print(f"Abstract length: {len(analysis.abstract)}")
print(f"Technologies: {analysis.technologies}")
```

**Expected Output:**

```
Title: [Paper Title - not "Untitled"]
Word Count: [>100]
Keywords: ['Term1', 'Term2', ...]  # Real terms
Abstract length: [>100]
Technologies: ['Python', 'TensorFlow']  # Real tech
```

**✓ If database has real data, analysis pipeline works**

---

### Test 6: Error Handling 🚨

#### Test Case 1: File Too Large

- Try uploading PDF > 50MB
- **Expected:** Error: "File too large"

#### Test Case 2: Wrong File Type

- Try uploading .docx or .txt as PDF
- **Expected:** Error: "Only PDF files allowed"

#### Test Case 3: Empty Text Input

- Submit empty or <50 char text
- **Expected:** Error: "Text too short"

#### Test Case 4: Invalid URL

- Enter "notaurl" in URL field
- **Expected:** Error: "Invalid URL"

**✓ If all errors handled gracefully, error handling works**

---

### Test 7: Library Page 📚

1. Navigate to `/library/`
2. Should see uploaded papers

**Expected:**

- [ ] All uploaded papers displayed
- [ ] Correct type badges (PDF/Text/URL)
- [ ] Extracted keywords shown
- [ ] Search functionality works
- [ ] Filter buttons work (PDF/Text)
- [ ] No template errors

**✓ If library loads without errors, Django templates fixed**

---

### Test 8: Profile & Dashboard 👤

1. Navigate to `/profile/`
2. Navigate to `/dashboard/`

**Expected:**

- [ ] Real stats displayed (not mock)
- [ ] Paper count matches database
- [ ] Plagiarism average calculated
- [ ] Weekly activity chart shows real data

**✓ If real data shows, profile/dashboard fixes work**

---

## Performance Testing ⚡

### Benchmark Your System

```bash
# Time analysis of a 15-page PDF (~5000 words)
# Start server with timestamps enabled
python manage.py runserver --verbosity=2
```

**Watch terminal output for timing:**

```
PDF extract took X.XXs
full_analysis took X.XXs
Database save took X.XXs
```

**Expected Times:**

- PDF Extraction: 2-5s
- NLP Analysis: 3-8s (with transformers) or 1-3s (lightweight)
- Database: 0.5s
- **TOTAL:** 6-15s

**If TOTAL > 30s:**

- [ ] Reduce `PDF_MAX_PAGES=20`
- [ ] Disable heavy models: `ENABLE_HEAVY_ML=False`
- [ ] Check CPU/RAM usage

---

## Verification Checklist

| Component    | Test                 | Result | Status |
| ------------ | -------------------- | ------ | ------ |
| Server Start | Django server starts | ✓      | ✅     |
| Frontend     | Homepage loads       | ✓      | ✅     |
| Upload Form  | Form renders         | ✓      | ✅     |
| PDF Upload   | Analyze completes    | ✓      | ✅     |
| Keywords     | Real extraction      | ✓      | ✅     |
| Summary      | AI generation        | ✓      | ✅     |
| Database     | Data saved           | ✓      | ✅     |
| Errors       | Handled gracefully   | ✓      | ✅     |
| Library      | Paper displayed      | ✓      | ✅     |
| Dashboard    | Real stats shown     | ✓      | ✅     |

---

## Common Issues & Fixes

### ❌ "Module not found: nltk"

```bash
pip install nltk
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### ❌ "No such file: manage.py"

```bash
# Make sure you're in the right directory
cd c:\Users\sanjn\paper\paper_analyzer
pwd  # Should end with paper_analyzer
```

### ❌ "Port 8000 already in use"

```bash
# Use different port
python manage.py runserver 0.0.0.0:8001
```

### ❌ "Template Syntax Error"

- Check that `templates/analyzer/library.html` has correct if/elif/endif blocks
- Django can't have elif inside {{ }} - must be separate template tags

### ❌ "Analysis takes too long (>30s)"

```env
# In .env or set environment variable:
ENABLE_HEAVY_ML=False
PDF_MAX_PAGES=20
```

### ❌ "Extracting fake keywords"

- Check that ml_processor.extract_keywords() uses TF-IDF, not random selection
- Verify NLTK data downloaded
- Test with shorter PDF first

---

## Quick Sanity Checks

### Test Keywords Are Real

```python
# In Django shell
from analyzer.models import AnalysisResult
analysis = AnalysisResult.objects.last()

# Check 1: Keywords should be related to paper content
print(f"Keywords: {analysis.keywords}")

# Check 2: Should have 5-15 keywords (not random)
print(f"Count: {len(analysis.keywords)}")

# Check 3: Each keyword should be in original text
from analyzer.models import Document
doc = analysis.document
original_text = doc.content.lower()
for kw in analysis.keywords:
    if kw.lower() in original_text:
        print(f"✓ {kw} found in text")
    else:
        print(f"✗ {kw} NOT found in text (SUSPICIOUS)")
```

### Test Summary Is Contextual

```python
# Summary should mention paper topic, not generic phrases
summary = analysis.summary

# Check for generic phrases
generic = ["this paper", "we propose", "research", "study"]
bad_phrases = [phrase for phrase in generic if phrase in summary.lower()]

if len(bad_phrases) > 3:
    print("⚠️ Summary might be too generic")
else:
    print("✓ Summary looks contextual")
```

### Test Technologies Are Detected

```python
# Should list real tech, not random
print(f"Technologies: {analysis.technologies}")

# Should relate to paper content
print(f"Methodology: {analysis.methodology}")
```

---

## Success Criteria

✅ **All Green = System Working Perfectly**

1. `PDF upload → Analysis completes in <20s`
2. `Keywords are real terms from paper (TF-IDF extracted)`
3. `Summary is contextual (BART generated)`
4. `Libraries show real stats`
5. `No errors in browser console`
6. `Database contains all analysis results`
7. `Progress bar updates smoothly`
8. `Errors handled with user messages`

---

## Next: Deploy & Monitor

Once testing passes:

1. Set `DEBUG=False` in settings.py
2. Configure allowed hosts
3. Use production WSGI server (Gunicorn/Waitress)
4. Enable HTTPS/SSL
5. Monitor `logs/django.log`
6. Set up error tracking (Sentry)

---

**🎉 If all tests pass, congratulations!**
Your research paper analyzer is fully functional with **REAL AI analysis**!
