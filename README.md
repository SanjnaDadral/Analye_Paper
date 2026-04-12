# PaperAIzer - AI-Powered Research Paper Analyzer

A premium SaaS-style web application for analyzing research papers using advanced NLP and machine learning. Supports PDF uploads, text pasting, and URL scraping with comprehensive AI-powered analysis.

![PaperAIzer Banner](https://img.shields.io/badge/PaperAIzer-AI%20Research%20Analyzer-667eea?style=for-the-badge&logo=robot&logoColor=white)

## Features

### Input Methods
- **PDF Upload**: Extract and analyze content from PDF research papers
- **Text Paste**: Paste raw text content for analysis
- **URL Input**: Scrape and analyze content from research paper URLs

### AI-Powered Analysis
- Automatic title and abstract extraction
- AI-generated summaries using BART model
- Keyword extraction using KeyBERT
- Methodology detection (ML, DL, NLP, CV, etc.)
- Technology detection
- Research goal and impact analysis
- Author extraction
- Publication year detection

### Smart Extraction
- Link extraction from documents
- Dataset name and link detection
- Reference extraction
- Document statistics (word count, unique words)

### Library System
- Store all analyzed documents
- Search and filter functionality
- Delete entries
- View saved results anytime

### Export System
- Export to PDF with professional formatting
- Export to plain text
- Email report via SMTP

## Tech Stack

**Backend:**
- Django 4.2+
- Python 3.9+

**Frontend:**
- HTML5, CSS3, JavaScript
- Bootstrap 5
- Font Awesome 6
- Custom glassmorphism design

**ML/NLP:**
- HuggingFace Transformers (BART)
- Sentence Transformers
- KeyBERT

**PDF Processing:**
- pdfplumber
- PyPDF2

**Web Scraping:**
- BeautifulSoup4
- Requests

**Export:**
- ReportLab

## Installation

### Prerequisites
- Python 3.9 or higher
- pip or pipenv

### Setup Steps

1. **Clone or navigate to the project directory:**
```bash
cd paper_analyzer
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run database migrations:**
```bash
python manage.py migrate
```

5. **Create a superuser (optional, for admin access):**
```bash
python manage.py createsuperuser
```

6. **Run the development server:**
```bash
python manage.py runserver
```

7. **Open your browser and navigate to:**
```
http://localhost:8000
```

## Configuration

### Email Settings (Optional)

Create a `.env` file in the `paper_analyzer` directory:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@paperyzer.ai
```

For Gmail, you'll need to generate an App Password from your Google Account settings.

### Secret Key (Production)

For production deployments, set a secure secret key:

```env
SECRET_KEY=your-super-secret-production-key
DEBUG=False
```

## Usage Guide

### Analyzing a PDF
1. Click "Upload PDF" tab
2. Drag and drop or click to select a PDF file
3. Click "Analyze with AI"
4. View the comprehensive results

### Analyzing Text
1. Click "Paste Text" tab
2. Paste your research paper content
3. Click "Analyze with AI"
4. View the comprehensive results

### Analyzing a URL
1. Click "Enter URL" tab
2. Paste a research paper URL
3. Click "Analyze with AI"
4. View the comprehensive results

### Managing Library
- Access all analyzed documents from the Library page
- Search by title or content
- Filter by input type (PDF, Text, URL)
- Delete unwanted entries
- View full analysis details

### Exporting Results
- Click "PDF" to download a formatted PDF report
- Click "TXT" to download plain text report
- Click "Email" to send report via email

## Project Structure

```
paper_analyzer/
├── analyzer/
│   ├── __init__.py
│   ├── admin.py          # Django admin configuration
│   ├── apps.py
│   ├── forms.py          # Form definitions
│   ├── models.py         # Database models
│   ├── views.py          # View functions
│   ├── urls.py           # URL routing
│   ├── ml_model.py       # ML/NLP processing
│   ├── pdf_processor.py  # PDF extraction
│   ├── url_scraper.py    # Web scraping
│   └── export_manager.py # Export functionality
├── media/
│   └── uploads/          # Uploaded files
├── paper_analyzer/
│   ├── __init__.py
│   ├── settings.py       # Django settings
│   ├── urls.py           # Root URL configuration
│   └── wsgi.py           # WSGI application
├── static/
│   ├── css/
│   │   └── styles.css    # Custom premium styles
│   └── js/
│       └── app.js        # JavaScript functionality
├── templates/
│   └── analyzer/
│       ├── base.html     # Base template
│       ├── home.html     # Home/upload page
│       ├── library.html  # Document library
│       ├── result.html   # Result detail page
│       └── partials/     # Template partials
├── db.sqlite3            # SQLite database
├── manage.py             # Django management script
└── requirements.txt     # Python dependencies
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page with upload form |
| `/analyze/` | POST | Analyze document |
| `/result/<id>/` | GET | View analysis result |
| `/library/` | GET | View document library |
| `/delete/<id>/` | GET | Delete document |
| `/export/<id>/pdf/` | GET | Export as PDF |
| `/export/<id>/txt/` | GET | Export as text |
| `/email/<id>/` | POST | Email report |
| `/health/` | GET | Health check |

## Performance Optimization

The application is optimized for:
- **Speed**: Uses lightweight models (DistilBART, MiniLM)
- **Memory**: Efficient processing with chunking
- **Compatibility**: Works on Google Colab and local systems

## Troubleshooting

### Common Issues

**Model download errors:**
- Ensure internet connection for first-time model downloads
- Models are cached locally after first download

**PDF extraction fails:**
- Ensure the PDF is not password-protected
- Try with a different PDF if extraction fails

**URL scraping issues:**
- Some websites may block scraping
- Try with publicly accessible research papers

### Getting Help

For issues or questions, please open an issue on the project repository.

## License

This project is for educational and research purposes.

## Credits

- Powered by HuggingFace Transformers
- UI design inspired by modern SaaS applications
- Built with Django and Bootstrap

---

**Made with AI & Python**
