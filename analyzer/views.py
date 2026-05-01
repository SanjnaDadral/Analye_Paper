
import logging
import os
import time
import re
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.conf import settings
from .rag_utils import rag_pipeline
from groq import Groq
# from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import UploadedFile


from .models import Document, AnalysisResult, PlagiarismCheck, AnalysisFeedback, ComparisonResult
from .plagiarism import local_library_similarity
from .forms import DocumentUploadForm, CustomRegistrationForm, EmailLoginForm
from .ml_model import ml_processor
from .pdf_processor import get_pdf_processor, extract_word_text, is_word_file, is_pdf_file
from .url_scraper import url_scraper
from .export_manager import export_manager
# from analyzer.utils.groq import analyze_text_with_groq
from analyzer.rag_utils import analyze_text_with_groq

logger = logging.getLogger(__name__)

ANALYSIS_TEXT_MAX = int(os.getenv("ANALYSIS_TEXT_CAP", "5000"))
TITLE_SAMPLE_CHARS = int(os.getenv("TITLE_SAMPLE_CHARS", "12000"))
MAX_PDF_UPLOAD_BYTES = int(os.getenv("MAX_PDF_UPLOAD_MB", "45")) * 1024 * 1024
MAX_PDF_STORE_BYTES = int(os.getenv("MAX_STORE_PDF_MB", "16")) * 1024 * 1024


# =========================
# 🔥 GROQ AI FUNCTION
# =========================
# def analyze_text_with_groq(text):
#     client = Groq(api_key=settings.GROQ_API_KEY)

#     prompt = f"""
#     Analyze the following research paper and provide a comprehensive JSON extraction.
#     Be extremely thorough in identifying all components.

#     Provide:
#     - summary: A clear, multi-sentence executive summary (80-120 words).
#     - abstract: The original or reconstructed abstract.
#     - keywords: Exhaustive list of 8-15 technical keywords.
#     - methodology: Detailed list of mathematical models, algorithms, or experimental setups used.
#     - technologies: Extensive list of software, libraries, hardware, and physical tools mentioned.
#     - goal: The primary research objective or hypothesis.
#     - impact: Potential contributions to the field and real-world applications.
#     - research_gaps: A list of 3-5 limitations or future work areas mentioned.
#     - conclusion: A summary of the final findings.
#     - datasets: List of any public or private datasets mentioned.
#     - authors: Full names of all identified authors.
#     - publication_year: The year of publication (4 digits).

#     TEXT:
#     {text[:20000]}
#     """

#     response = client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[
#             {"role": "system", "content": "Return only valid JSON object, no markdown formatting."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.3,
#     )

#     content = response.choices[0].message.content
    
#     # Clean up JSON - remove markdown code blocks if present
#     content = content.strip()
#     if content.startswith('```'):
#         content = content.split('```')[1]
#         if content.startswith('json'):
#             content = content[4:]
#         content = content.strip()
#     if content.endswith('```'):
#         content = content[:-3].strip()

#     try:
#         data = json.loads(content)
#     except json.JSONDecodeError as e:
#         logger.warning(f"JSON parse error: {e}, content: {content[:200]}")
#         data = {
#             "summary": content[:500] if content else "",
#             "abstract": "",
#             "keywords": [],
#             "methodology": [],
#             "technologies": [],
#             "goal": "",
#             "impact": "",
#             "authors": [],
#             "publication_year": ""
#         }

#     # Add required stats
#     data["statistics"] = {
#         "word_count": len(text.split()),
#         "unique_words": len(set(text.split()))
#     }

#     return data


# =========================
# VALIDATE PDF
# =========================
# def validate_pdf_file(file):
#     if not file:
#         return False, "No file provided"

#     if not file.name.lower().endswith('.pdf'):
#         return False, "Only PDF files allowed"

#     if file.size > MAX_PDF_UPLOAD_BYTES:
#         return False, "File too large"

#     return True, None

# import logging

# logger = logging.getLogger(__name__)

MAX_PDF_UPLOAD_BYTES = 52 * 1024 * 1024  # 52 MB - keep consistent with settings.py

def validate_pdf_file(file):
    """Validate uploaded PDF or Word file safely"""
    if not file:
        logger.warning("validate_pdf_file: No file provided")
        return False, "No file provided"

    # Check if it's a real UploadedFile object
    if not hasattr(file, 'name') or not hasattr(file, 'size'):
        logger.warning("validate_pdf_file: Invalid file object")
        return False, "Invalid file uploaded"

    # Check extension
    fname = file.name.lower()
    if not (fname.endswith('.pdf') or fname.endswith('.docx') or fname.endswith('.doc')):
        logger.warning(f"validate_pdf_file: Unsupported format - filename: {file.name}")
        return False, "Only PDF and Word (.docx, .doc) files are allowed"

    # Check size
    file_size = getattr(file, 'size', 0)
    if file_size == 0:
        logger.warning("validate_pdf_file: Empty file")
        return False, "Uploaded file is empty"

    if file_size > MAX_PDF_UPLOAD_BYTES:
        logger.warning(f"validate_pdf_file: File too large - size: {file_size / (1024*1024):.2f} MB")
        return False, f"File too large (max {MAX_PDF_UPLOAD_BYTES // (1024*1024)} MB)"

    logger.info(f"validate_pdf_file: File passed validation - {file.name} ({file_size / (1024*1024):.2f} MB)")
    return True, None
# =========================
# HOME
# =========================
def home(request):
    form = DocumentUploadForm()
    docs = []
    if request.user.is_authenticated:
        docs = Document.objects.filter(user=request.user).order_by('-created_at')[:6]

    return render(request, 'analyzer/home.html', {'form': form, 'recent_docs': docs})


# =========================
# LOGIN
# =========================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = EmailLoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')

    return render(request, 'analyzer/login.html', {'form': form})


# def login_view(request):
#     if request.user.is_authenticated:
#         return redirect('dashboard')

#     form = AuthenticationForm(request, data=request.POST or None)

#     if request.method == 'POST':
#         if form.is_valid():
#             user = form.get_user()
#             login(request, user)
#             return redirect('dashboard')
#         else:
#             return render(request, 'analyzer/login.html', {
#                 'form': form,
#                 'error': 'Invalid username or password'
#             })

#     return render(request, 'analyzer/login.html', {'form': form})

# def login_view(request):
#     if request.user.is_authenticated:
#         return redirect('dashboard')

#     form = AuthenticationForm(request, data=request.POST or None)

#     if request.method == 'POST' and form.is_valid():
#         login(request, form.get_user())
#         return redirect('dashboard')

#     return render(request, 'analyzer/login.html', {'form': form})
# def login_view(request):
#     if request.user.is_authenticated:
#         return redirect('dashboard')

#     form = AuthenticationForm(request, data=request.POST or None)

#     if request.method == 'POST' and form.is_valid():
#         login(request, form.get_user())
#         next_url = request.POST.get('next') or request.GET.get('next')
#         return redirect(next_url if next_url else 'dashboard')  # ✅ respects ?next=

#     return render(request, 'analyzer/login.html', {'form': form})
# =========================
# REGISTER
# =========================
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = CustomRegistrationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        try:
            from django.db import IntegrityError
            user = form.save()
            login(request, user)
            return redirect('dashboard')
        except IntegrityError:
            form.add_error('email', 'An account with this email already exists.')

    return render(request, 'analyzer/register.html', {'form': form})


# =========================
# LOGOUT
# =========================
@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect('home')


# =========================
# 🔥 MAIN ANALYSIS (UPDATED)
# =========================
# @require_http_methods(["POST"])
# def analyze_document(request):
#     if not request.user.is_authenticated:
#         return JsonResponse({'error': 'Login required'}, status=401)

#     try:
#         uploaded_file = request.FILES.get('pdf_file')

#         is_valid, error = validate_pdf_file(uploaded_file)
#         if not is_valid:
#             return JsonResponse({'error': error}, status=400)

#         # Extract text
#         result = pdf_processor.extract_text(uploaded_file)
#         if not result.get('success'):
#             return JsonResponse({'error': 'PDF extraction failed'}, status=400)

#         content = result.get('text', '')[:ANALYSIS_TEXT_MAX]

#         # Save document
#         document = Document.objects.create(
#             user=request.user,
#             title="Analyzed Document",
#             content=content,
#             word_count=len(content.split())
#         )

#         # =========================
#         # 🔥 GROQ + FALLBACK ML
#         # =========================
#         try:
#             analysis_data = analyze_text_with_groq(content)
#         except Exception as e:
#             logger.warning(f"Groq failed: {e}")
#             analysis_data = ml_processor.full_analysis(content)

#         # Plagiarism
#         plagiarism = local_library_similarity(document.id, content, user=request.user)

#         PlagiarismCheck.objects.create(
#             document=document,
#             similarity_score=plagiarism.get("similarity_percent", 0) / 100.0,
#         )

#         # Save analysis
#         analysis = AnalysisResult.objects.create(
#             document=document,
#             summary=analysis_data.get('summary', ''),
#             abstract=analysis_data.get('abstract', ''),
#             keywords=analysis_data.get('keywords', []),
#             methodology=analysis_data.get('methodology', []),
#             technologies=analysis_data.get('technologies', []),
#             goal=analysis_data.get('goal', ''),
#             impact=analysis_data.get('impact', ''),
#             publication_year=analysis_data.get('publication_year', ''),
#             authors=analysis_data.get('authors', []),
#             word_count=analysis_data.get('statistics', {}).get('word_count', 0),
#             unique_words=analysis_data.get('statistics', {}).get('unique_words', 0),
#         )

#         return JsonResponse({
#             'success': True,
#             'redirect_url': f'/result/{document.id}/'
#         })

#     except Exception as e:
#         logger.error(e, exc_info=True)
#         return JsonResponse({'error': str(e)}, status=500)

# from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import UploadedFile

# logger = logging.getLogger(__name__)

@csrf_exempt
def analyze_document(request):
    """Main document analysis endpoint - Handles PDF upload and URL input"""
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    # Log incoming request for easier debugging
    logger.info(f"Analyze request received - Method: {request.method}, Content-Type: {request.content_type}")
    logger.info(f"POST keys: {list(request.POST.keys())}")
    logger.info(f"POST values: {dict(request.POST)}")
    logger.info(f"FILES keys: {list(request.FILES.keys())}")
    logger.info(f"FILES values: {dict(request.FILES)}")
    logger.info(f"Request META content length: {request.META.get('CONTENT_LENGTH', 'Not set')}")
    logger.info(f"Request META content type: {request.META.get('CONTENT_TYPE', 'Not set')}")

    try:
        input_type = request.POST.get('input_type', 'pdf').strip().lower()
        logger.info(f"Processing input_type: {input_type}")
        
        # Debug: log what files are received
        logger.info(f"FILES keys: {list(request.FILES.keys())}")
        
        # Debug: check each input type
        if input_type == 'pdf':
            logger.info(f"pdf_file in FILES: {'pdf_file' in request.FILES}")
        elif input_type == 'bulk':
            logger.info(f"bulk_files in FILES: {'bulk_files' in request.FILES}")
        elif input_type == 'url':
            logger.info(f"url_input in POST: {'url_input' in request.POST}")

        content = None
        title = "Analyzed Document"
        document_input_type = 'pdf'
        url_source = None
        result = None  # Will hold scraper/processor result dict

        # =========================
        # 📄 PDF UPLOAD
        # =========================
        if input_type == 'pdf':
            uploaded_file: UploadedFile = request.FILES.get('pdf_file')
            logger.info(f"PDF upload attempt - uploaded_file: {uploaded_file}")

            if not uploaded_file:
                logger.warning("No PDF file uploaded - returning error")
                return JsonResponse({
                    'error': 'No PDF file uploaded. Please select a PDF file before submitting.',
                    'debug_info': {
                        'input_type': input_type,
                        'files_received': list(request.FILES.keys()),
                        'post_data': list(request.POST.keys())
                    }
                }, status=400)

            # Validate file
            is_valid, error_msg = validate_pdf_file(uploaded_file)
            if not is_valid:
                logger.warning(f"PDF validation failed: {error_msg}")
                return JsonResponse({'error': error_msg}, status=400)

            # Process PDF or Word
            if is_word_file(uploaded_file.name):
                result = extract_word_text(uploaded_file)
            else:
                processor = get_pdf_processor()
                result = processor.extract_text(uploaded_file)

            if not result.get('success'):
                logger.error(f"File extraction failed: {result.get('error')}")
                return JsonResponse({'error': result.get('error', 'Failed to extract text from file')}, status=400)

            content = result.get('text', '')[:ANALYSIS_TEXT_MAX]
            
            # Validate content length
            if not content or len(content.strip()) < 30:
                logger.warning(f"Content validation failed - content length: {len(content) if content else 0}")
                return JsonResponse({
                    'error': f'Not enough content extracted from the file (minimum 30 characters). Extracted: {len(content) if content else 0} characters. This may be a scanned PDF or image-based document that requires OCR.'
                }, status=400)

        # =========================
        # 📄 BULK PDF UPLOAD
        # =========================
        elif input_type == 'bulk':
            bulk_files = request.FILES.getlist('bulk_files')
            
            if not bulk_files:
                return JsonResponse({'error': 'No files uploaded for bulk processing'}, status=400)
            
            if len(bulk_files) > 5:
                return JsonResponse({'error': 'Maximum 5 files allowed for bulk upload'}, status=400)
            
            # Process all files - create separate documents for each
            processor = get_pdf_processor()
            document_ids = []
            
            for idx, uploaded_file in enumerate(bulk_files):
                # Validate file
                is_valid, error_msg = validate_pdf_file(uploaded_file)
                if not is_valid:
                    logger.warning(f"PDF validation failed: {error_msg}")
                    return JsonResponse({'error': f'File {uploaded_file.name}: {error_msg}'}, status=400)

                # Process PDF or Word
                if is_word_file(uploaded_file.name):
                    result = extract_word_text(uploaded_file)
                else:
                    result = processor.extract_text(uploaded_file)

                if not result.get('success'):
                    logger.error(f"File extraction failed: {result.get('error')}")
                    return JsonResponse({'error': f'Failed to extract text from {uploaded_file.name}: {result.get("error", "")}'}, status=400)

                content = result.get('text', '')[:ANALYSIS_TEXT_MAX]
                
                # Validate content length
                if not content or len(content.strip()) < 30:
                    logger.warning(f"Content validation failed for {uploaded_file.name} - content length: {len(content) if content else 0}")
                    return JsonResponse({
                        'error': f'Not enough content extracted from {uploaded_file.name} (minimum 30 characters). Extracted: {len(content) if content else 0} characters. This may be a scanned PDF or image-based document.'
                    }, status=400)
                
                title = f"Bulk Upload - {uploaded_file.name}"
                
                # Create document for each file
                document = Document.objects.create(
                    user=request.user,
                    input_type='pdf',
                    title=title,
                    content=content,
                    url=None,
                    word_count=len(content.split())
                )
                document_ids.append(document.id)
                
                # Process analysis for this document
                try:
                    analysis_data = analyze_text_with_groq(content)
                except Exception as e:
                    logger.warning(f"Groq failed: {e}")
                    try:
                        analysis_data = ml_processor.full_analysis(content)
                    except Exception as fallback_e:
                        logger.error(f"Fallback ML also failed: {fallback_e}")
                        analysis_data = {
                            'summary': 'Analysis could not be completed due to technical issues.',
                            'abstract': '', 'keywords': [], 'methodology': [],
                            'technologies': [], 'goal': '', 'impact': '',
                            'publication_year': '', 'authors': [],
                            'statistics': {'word_count': len(content.split()), 'unique_words': 0},
                            'research_gaps': [], 'conclusion': ''
                        }

                # Plagiarism check
                plagiarism = local_library_similarity(document.id, content, user=request.user)

                PlagiarismCheck.objects.create(
                    document=document,
                    similarity_score=plagiarism.get("similarity_percent", 0) / 100.0,
                )

                # Save analysis result with same fields as single upload
                AnalysisResult.objects.create(
                    document=document,
                    summary=analysis_data.get('summary', ''),
                    abstract=analysis_data.get('abstract', ''),
                    keywords=analysis_data.get('keywords', []),
                    methodology=analysis_data.get('methodology', []),
                    technologies=analysis_data.get('technologies', []),
                    goal=analysis_data.get('goal', ''),
                    impact=analysis_data.get('impact', ''),
                    publication_year=analysis_data.get('publication_year', ''),
                    authors=analysis_data.get('authors', []),
                    word_count=analysis_data.get('statistics', {}).get('word_count', 0),
                    unique_words=analysis_data.get('statistics', {}).get('unique_words', 0),
                    extracted_links=result.get('extracted_links', []),
                    references=getattr(ml_processor, 'extract_references', lambda x: [])(content),
                    extras={
                        'plagiarism': plagiarism,
                        'research_gaps': analysis_data.get('research_gaps', []),
                        'conclusion': analysis_data.get('conclusion', ''),
                        'extracted_images': result.get('extracted_images', [])
                    }
                )
            
            logger.info(f"Bulk processing completed: {len(document_ids)} documents for user {request.user.id}")
            
            ids_str = ','.join(str(i) for i in document_ids)
            return JsonResponse({
                'success': True,
                'message': f'Analysis of {len(document_ids)} paper{"s" if len(document_ids) > 1 else ""} complete!',
                'document_ids': document_ids,
                'redirect_url': f'/bulk-results/?ids={ids_str}'
            })



        elif input_type == 'url':
            url_input = request.POST.get('url_input', '').strip()

            if not url_input:
                return JsonResponse({'error': 'No URL provided'}, status=400)

            if not url_input.startswith(('http://', 'https://')):
                return JsonResponse({'error': 'URL must start with http:// or https://'}, status=400)

            try:
                scrape_result = url_scraper.scrape(url_input)
                if not scrape_result.get('success'):
                    error_msg = scrape_result.get('error', 'Unknown error')
                    logger.warning(f"URL scraping failed for {url_input}: {error_msg}")
                    # If the scraper already returned a user-friendly message, use it directly
                    if 'not supported' in error_msg.lower() or 'please provide' in error_msg.lower():
                        return JsonResponse({'error': error_msg}, status=400)
                    return JsonResponse({
                        'error': f'Could not extract content from this URL. The site may block automated access. Try downloading the PDF directly instead. Details: {error_msg}'
                    }, status=400)

                # URL Scraper may return 'content' or 'text' key
                raw_text = scrape_result.get('content') or scrape_result.get('text') or ''
                content = raw_text[:ANALYSIS_TEXT_MAX]
                url_source = url_input
                document_input_type = 'url'
                title = scrape_result.get('title') or 'Analyzed URL Paper'
                result = scrape_result  # keep reference for later

            except Exception as e:
                logger.error(f"URL scraping exception for {url_input}: {e}", exc_info=True)
                return JsonResponse({'error': f'URL processing failed: {str(e)}'}, status=400)

        else:
            return JsonResponse({'error': 'Invalid input type. Use "pdf", "url", or "bulk"'}, status=400)

        # =========================
        # CONTENT VALIDATION
        # =========================
        if not content or len(content.strip()) < 30:
            logger.warning(f"Content validation failed - content length: {len(content) if content else 0}")
            return JsonResponse({
                'error': f'Not enough content extracted from the document (minimum 30 characters). Extracted: {len(content) if content else 0} characters. This may be a scanned PDF or image-based document.'
            }, status=400)

        # =========================
        # GENERATE TITLE
        # =========================
        for line in content.splitlines():
            line = line.strip()
            if 5 < len(line) < 200:
                title = line[:150]
                break

        if title == "Analyzed Document":
            words = content.split()
            title = ' '.join(words[:12]) if words else "Analyzed Document"

        # =========================
        # SAVE DOCUMENT
        # =========================
        document = Document.objects.create(
            user=request.user,
            input_type=document_input_type,
            title=title,
            content=content,
            url=url_source,
            word_count=len(content.split())
        )

        # AI ANALYSIS
        # =========================
        try:
            analysis_data = analyze_text_with_groq(content)
            logger.info("Groq analysis completed successfully")
        except Exception as e:
            logger.warning(f"Groq failed: {e}")
            try:
                analysis_data = ml_processor.full_analysis(content)
            except Exception as fallback_e:
                logger.error(f"Fallback ML also failed: {fallback_e}")
                analysis_data = {
                    'summary': 'Analysis could not be completed due to technical issues.',
                    'abstract': '', 'keywords': [], 'methodology': [],
                    'technologies': [], 'goal': '', 'impact': '',
                    'publication_year': '', 'authors': [],
                    'statistics': {'word_count': len(content.split()), 'unique_words': 0},
                    'research_gaps': [], 'conclusion': ''
                }
        
        # Extra safety check
        if isinstance(analysis_data, str):
            analysis_data = {
                'summary': str(analysis_data)[:1000],
                'abstract': '',
                'keywords': [],
                'methodology': [],
                'technologies': [],
                'goal': '',
                'impact': '',
                'publication_year': '',
                'authors': [],
                'statistics': {'word_count': len(content.split()), 'unique_words': 0},
                'research_gaps': [],
                'conclusion': ''
            }

        # PLAGIARISM CHECK
        plagiarism = local_library_similarity(document.id, content, user=request.user)

        PlagiarismCheck.objects.create(
            document=document,
            similarity_score=plagiarism.get("similarity_percent", 0) / 100.0,
        )

        # Safely get extracted links and images
        pdf_extracted_links = result.get('extracted_links', []) if result else []
        pdf_extracted_images = result.get('extracted_images', []) if result and input_type == 'pdf' else []

        # SAVE ANALYSIS RESULT
        analysis = AnalysisResult.objects.create(
            document=document,
            summary=analysis_data.get('summary', ''),
            abstract=analysis_data.get('abstract', ''),
            keywords=analysis_data.get('keywords', []),
            methodology=analysis_data.get('methodology', []),
            technologies=analysis_data.get('technologies', []),
            goal=analysis_data.get('goal', ''),
            impact=analysis_data.get('impact', ''),
            publication_year=analysis_data.get('publication_year', ''),
            authors=analysis_data.get('authors', []),
            word_count=analysis_data.get('statistics', {}).get('word_count', 0),
            unique_words=analysis_data.get('statistics', {}).get('unique_words', 0),
            extracted_links=pdf_extracted_links,
            references=getattr(ml_processor, 'extract_references', lambda x: [])(content),
            extras={
                'plagiarism': plagiarism,
                'research_gaps': analysis_data.get('research_gaps', []),
                'conclusion': analysis_data.get('conclusion', ''),
                'extracted_images': pdf_extracted_images
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Analysis completed successfully',
            'document_id': document.id,
            'redirect_url': f'/result/{document.id}/'
        })

    except Exception as e:
        logger.error(f"Unexpected error in analyze_document: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An unexpected error occurred during analysis. Please try again.'
        }, status=500)


# =========================
# 📊 STUB FUNCTIONS (TODO)
# =========================

@login_required
def profile(request):
    """User profile page with edit functionality"""
    from .models import UserProfile, AnalysisResult, PlagiarismCheck
    from django.db.models import Sum, Avg
    from collections import Counter

    user = request.user
    profile_obj, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # Update User fields
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        new_email = request.POST.get('email', user.email).strip().lower()

        if new_email != user.email:
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                from django.contrib import messages as msg
                msg.error(request, 'That email is already in use by another account.')
                return redirect('profile')
            user.email = new_email
            user.username = new_email  # keep username == email

        user.save()

        # Update UserProfile fields
        profile_obj.bio = request.POST.get('bio', '').strip()[:500]
        profile_obj.institution = request.POST.get('institution', '').strip()[:200]
        profile_obj.research_interests = request.POST.get('research_interests', '').strip()[:300]
        profile_obj.website = request.POST.get('website', '').strip()

        if 'avatar' in request.FILES:
            profile_obj.avatar = request.FILES['avatar']

        profile_obj.save()

        from django.contrib import messages as msg
        msg.success(request, 'Profile updated successfully!')
        return redirect('profile')

    # Stats for display
    documents = Document.objects.filter(user=user)
    total_papers = documents.count()
    total_words = documents.aggregate(Sum('word_count'))['word_count__sum'] or 0

    analysis_results = AnalysisResult.objects.filter(document__user=user)
    all_keywords = []
    for a in analysis_results:
        all_keywords.extend(a.keywords or [])
    unique_keywords = len(set(all_keywords))

    plagiarism_checks = PlagiarismCheck.objects.filter(document__in=documents)
    avg_plagiarism = plagiarism_checks.aggregate(Avg('similarity_score'))['similarity_score__avg']
    avg_plagiarism = round(avg_plagiarism * 100, 1) if avg_plagiarism else 0

    return render(request, 'analyzer/profile.html', {
        'profile': profile_obj,
        'documents': documents.order_by('-created_at'),
        'total_papers': total_papers,
        'total_words': total_words,
        'unique_keywords': unique_keywords,
        'avg_plagiarism': avg_plagiarism,
        'member_since': user.date_joined,
    })


@login_required
def dashboard(request):
    """Dashboard page"""
    from django.utils import timezone
    from django.db.models import Count, Avg, Sum
    from datetime import timedelta
    import json as _json

    user = request.user

    # Total papers
    total_papers = Document.objects.filter(user=user).count()


    # Recent activity for sidebar
    recent_activity = Document.objects.filter(user=user).order_by('-created_at')[:5]
    documents = Document.objects.filter(user=user)

    # Total words
    total_words = documents.aggregate(Sum('word_count'))['word_count__sum'] or 0

    # Average words per paper
    avg_words = total_words / total_papers if total_papers > 0 else 0

    # This month papers
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = Document.objects.filter(user=user, created_at__gte=month_start).count()

    # Plagiarism stats
    from .models import PlagiarismCheck
    user_docs = Document.objects.filter(user=user)
    plagiarism_checks = PlagiarismCheck.objects.filter(document__in=user_docs)

    avg_plagiarism = plagiarism_checks.aggregate(Avg('similarity_score'))['similarity_score__avg']
    avg_plagiarism = round(avg_plagiarism * 100, 1) if avg_plagiarism else 0

    low_plag = plagiarism_checks.filter(similarity_score__lt=0.25).count()
    high_plag = plagiarism_checks.filter(similarity_score__gte=0.50).count()

    # Top keywords
    from .models import AnalysisResult
    analysis_results = AnalysisResult.objects.filter(document__user=user)
    all_keywords = []
    for a in analysis_results:
        all_keywords.extend(a.keywords or [])

    from collections import Counter
    keyword_counts = Counter(all_keywords)
    top_keywords = keyword_counts.most_common(10)

    # Unique keywords count
    unique_keywords = len(set(all_keywords))

    # Member since
    member_since = user.date_joined

    # User display name — first_name preferred, fallback to email prefix
    display_name = (user.first_name or '').strip() or user.email.split('@')[0]

    # Avatar initial — use first_name initial, fallback to email
    avatar_initial = ((user.first_name or '').strip() or user.email)[0].upper()

    # Monthly chart data — papers per month for last 6 months
    chart_labels = []
    chart_data = []
    for i in range(5, -1, -1):
        month_date = (now.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        if month_date.month == 12:
            next_month = month_date.replace(year=month_date.year + 1, month=1)
        else:
            next_month = month_date.replace(month=month_date.month + 1)
        count = Document.objects.filter(
            user=user,
            created_at__gte=month_date,
            created_at__lt=next_month
        ).count()
        chart_labels.append(month_date.strftime('%b %Y'))
        chart_data.append(count)

    # UserProfile
    from .models import UserProfile
    profile_obj, _ = UserProfile.objects.get_or_create(user=user)

    return render(request, 'analyzer/dashboard.html', {
        'total_papers': total_papers,
        'avg_plagiarism': avg_plagiarism,
        'unique_keywords': unique_keywords,
        'this_month': this_month,
        'recent_activity': recent_activity,
        'documents': documents,
        'total_words': total_words,
        'avg_words': round(avg_words),
        'low_plag': low_plag,
        'high_plag': high_plag,
        'top_keywords': top_keywords,
        'member_since': member_since,
        'user_full_name': display_name,
        'display_name': display_name,
        'avatar_initial': avatar_initial,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'profile': profile_obj,
    })


@login_required
def upload_page(request):
    """Upload page"""
    return render(request, 'analyzer/upload.html')


@login_required
def compare(request):
    """Compare papers page"""
    documents = Document.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'analyzer/compare.html', {'documents': documents})


def contact(request):
    """Contact page - Save messages to database"""
    from .models import ContactMessage
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not all([name, email, message]):
            return JsonResponse({'success': False, 'message': 'Please fill out all required fields.'})
        
        try:
            # Save contact message to database
            contact_msg = ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject or 'No Subject',
                message=message,
                is_read=False
            )
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Contact message saved from {name} ({email}): {subject}")
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you! Your message has been sent successfully. We will get back to you soon.'
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error saving contact message: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'An error occurred. Please try again.'
            })
    return render(request, 'analyzer/contact.html')


def forgot_password(request):
    """Forgot password page - Send OTP"""
    from .otp_utils import create_and_send_otp

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return redirect('forgot_password')

        try:
            User.objects.get(email__iexact=email)

            # Create OTP (always succeeds if DB is up)
            reset_otp, email_sent = create_and_send_otp(email)

            if reset_otp is not None:
                # OTP was created — store email in session and redirect to verify page
                request.session['reset_email'] = email
                if email_sent:
                    messages.success(request, f'An OTP has been sent to {email}. Check your inbox.')
                else:
                    # Simulator mode: OTP printed to server console
                    messages.success(request, f'OTP generated for {email}. (Check server console if running locally.)')
                return redirect('verify_otp')
            else:
                messages.error(request, 'Could not generate OTP. Please try again later.')
                return redirect('forgot_password')

        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
            return redirect('forgot_password')
        except Exception as e:
            logger.error(f"Forgot password error: {e}", exc_info=True)
            messages.error(request, 'An error occurred. Please try again.')
            return redirect('forgot_password')

    return render(request, 'analyzer/forgot_password.html')


def verify_otp(request):
    """Verify OTP page"""
    from .otp_utils import verify_otp as verify_otp_code, mark_otp_as_used
    
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Invalid request. Please start password reset again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        
        # Verify OTP
        is_valid, reset_otp_obj = verify_otp_code(email, otp)
        
        if is_valid:
            # Mark OTP as used
            mark_otp_as_used(email, otp)
            request.session['otp_verified'] = True
            messages.success(request, 'OTP verified successfully. Please set your new password.')
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid or expired OTP. Please try again.')
    
    context = {'email': email}
    return render(request, 'analyzer/verify_otp.html', context)


def reset_password(request):
    """Reset password page"""
    from django.contrib.auth import authenticate, update_session_auth_hash
    
    email = request.session.get('reset_email')
    otp_verified = request.session.get('otp_verified')
    
    if not email or not otp_verified:
        messages.error(request, 'Invalid request. Please start password reset again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate passwords
        if not password:
            messages.error(request, 'Password cannot be empty.')
        elif len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        else:
            # Update user password
            try:
                user = User.objects.get(email=email)
                user.set_password(password)
                user.save()
                
                # Clear session
                request.session.pop('reset_email', None)
                request.session.pop('otp_verified', None)
                
                messages.success(request, 'Password reset successfully! Please log in with your new password.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
    
    context = {'email': email}
    return render(request, 'analyzer/reset_password.html', context)


@login_required
def bulk_results(request):
    """Show results for all documents from a bulk upload session."""
    ids_param = request.GET.get('ids', '')
    if not ids_param:
        return redirect('library')
    try:
        doc_ids = [int(i) for i in ids_param.split(',') if i.strip().isdigit()]
    except ValueError:
        return redirect('library')
    documents = Document.objects.filter(id__in=doc_ids, user=request.user).prefetch_related('analysis')
    # Preserve original order
    doc_map = {d.id: d for d in documents}
    ordered = [doc_map[i] for i in doc_ids if i in doc_map]
    return render(request, 'analyzer/bulk_results.html', {'documents': ordered})


@login_required
def result_detail(request, document_id):
    """Detailed result page for a document"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    analysis = getattr(document, 'analysis', None)
    return render(request, 'analyzer/result.html', {'document': document, 'analysis': analysis})


@login_required
def ask_question(request, document_id):
    """Answer a specific question about a document using RAG"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        question = data.get('question')
        
        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)
            
        document = get_object_or_404(Document, id=document_id, user=request.user)
        
        # Use the RAG pipeline to get an answer
        answer = rag_pipeline(document.content, question)
        if isinstance(answer, dict):
            answer = answer.get('summary', str(answer))
        
        return JsonResponse({'success': True, 'question': question, 'answer': answer})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Q&A Error for doc {document_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)



@login_required
def compare_papers(request, doc1_id, doc2_id):
    """Compare two papers - returns JSON data for comparison"""
    if doc1_id == doc2_id:
        return JsonResponse({'error': 'Cannot compare a paper with itself'}, status=400)
        
    doc1 = get_object_or_404(Document, id=doc1_id, user=request.user)
    doc2 = get_object_or_404(Document, id=doc2_id, user=request.user)
    
    # Get analysis data
    analysis1 = getattr(doc1, 'analysis', None)
    analysis2 = getattr(doc2, 'analysis', None)
    
    # Helper function to get keywords/methods as list
    def to_list(value):
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            return [value] if value else []
        return []
    
    # Helper function to calculate similarity
    def calculate_similarity(list1, list2):
        if not list1 or not list2:
            return 0
        common = len(set(str(x).lower() for x in list1) & set(str(x).lower() for x in list2))
        total = max(len(list1), len(list2))
        return int((common / total) * 100) if total > 0 else 0
    
    # Extract data with fallbacks
    p1_data = {
        'id': doc1.id,
        'title': doc1.title or 'Untitled',
        'authors': ', '.join(to_list(analysis1.authors)) if analysis1 else 'Unknown',
        'publication_date': analysis1.publication_year if analysis1 else 'Unknown',
        'word_count': analysis1.word_count if analysis1 else doc1.word_count,
        'abstract': (analysis1.abstract or 'No abstract available') if analysis1 else 'No content',
        'keywords': to_list(analysis1.keywords) if analysis1 else [],
        'methodology': to_list(analysis1.methodology) if analysis1 else [],
        'technologies': to_list(analysis1.technologies) if analysis1 else [],
        'summary': analysis1.summary if analysis1 else ''
    }
    
    p2_data = {
        'id': doc2.id,
        'title': doc2.title or 'Untitled',
        'authors': ', '.join(to_list(analysis2.authors)) if analysis2 else 'Unknown',
        'publication_date': analysis2.publication_year if analysis2 else 'Unknown',
        'word_count': analysis2.word_count if analysis2 else doc2.word_count,
        'abstract': (analysis2.abstract or 'No abstract available') if analysis2 else 'No content',
        'keywords': to_list(analysis2.keywords) if analysis2 else [],
        'methodology': to_list(analysis2.methodology) if analysis2 else [],
        'technologies': to_list(analysis2.technologies) if analysis2 else [],
        'summary': analysis2.summary if analysis2 else ''
    }
    
    # Calculate similarities
    keyword_sim = calculate_similarity(p1_data['keywords'], p2_data['keywords'])
    method_sim = calculate_similarity(p1_data['methodology'], p2_data['methodology'])
    tech_sim = calculate_similarity(p1_data['technologies'], p2_data['technologies'])
    overall_sim = int((keyword_sim + method_sim + tech_sim) / 3)
    
    # Find common elements
    common_keywords = list(set(str(x).lower() for x in p1_data['keywords']) & set(str(x).lower() for x in p2_data['keywords']))
    common_methods = list(set(str(x).lower() for x in p1_data['methodology']) & set(str(x).lower() for x in p2_data['methodology']))
    common_tech = list(set(str(x).lower() for x in p1_data['technologies']) & set(str(x).lower() for x in p2_data['technologies']))
    
    # Find unique elements
    unique_p1_kw = list(set(str(x).lower() for x in p1_data['keywords']) - set(str(x).lower() for x in p2_data['keywords']))
    unique_p2_kw = list(set(str(x).lower() for x in p2_data['keywords']) - set(str(x).lower() for x in p1_data['keywords']))
    
    comparison_result = {
        'overall_similarity': overall_sim,
        'keyword_similarity': keyword_sim,
        'method_similarity': method_sim,
        'tech_similarity': tech_sim,
        'common_keywords': common_keywords[:10],
        'common_methods': common_methods[:10],
        'common_tech': common_tech[:10],
        'unique_p1': unique_p1_kw[:10],
        'unique_p2': unique_p2_kw[:10]
    }
    
    # Save comparison result to database
    from .models import ComparisonResult
    try:
        ComparisonResult.objects.create(
            user=request.user,
            document1=doc1,
            document2=doc2,
            similarity_score=overall_sim,
            comparison_data=comparison_result
        )
    except Exception as e:
        logger.error(f"Error saving comparison result: {str(e)}")
    
    return JsonResponse({
        'paper1': p1_data,
        'paper2': p2_data,
        'comparison': comparison_result
    })

@login_required
def email_report(request, document_id):
    """Email analysis report to user or recipient"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    analysis = getattr(document, 'analysis', None)
    
    if request.method == 'POST':
        recipient = request.POST.get('email', request.user.email)
        export_format = request.POST.get('export_format', 'pdf')
        
        if not recipient:
            return JsonResponse({'success': False, 'error': 'No recipient email provided'})
            
        try:
            # Generate the biological attachment
            if export_format == 'pdf':
                response = export_as_pdf(request, document, analysis)
                filename = f"{document.title[:30]}_report.pdf"
                mimetype = 'application/pdf'
            else:
                response = export_as_txt(document, analysis)
                filename = f"{document.title[:30]}_report.txt"
                mimetype = 'text/plain'
            
            from django.core.mail import EmailMessage
            
            subject = f"PaperAIzer Report: {document.title}"
            body = f"Hello,\n\nPlease find attached the analysis report for '{document.title}' generated by PaperAIzer.\n\nBest regards,\nThe PaperAIzer Team"
            
            email = EmailMessage(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
            )
            email.attach(filename, response.content, mimetype)
            email.send()
            
            return JsonResponse({'success': True, 'message': f'Report sent successfully to {recipient}'})
        except Exception as e:
            logger.error(f"Email report error: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': f'Failed to send email: {str(e)}'})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)



@login_required
def library(request):
    """Library page - list of all user documents"""
    documents = Document.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'analyzer/library.html', {'documents': documents})


@login_required
def delete_document(request, document_id):
    """Delete a document"""
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)
        if request.method == 'POST':
            document.delete()
            return JsonResponse({'success': True, 'message': 'Document deleted successfully'})
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def export_document(request, document_id, export_format):
    """Export document in specified format"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    analysis = getattr(document, 'analysis', None)
    
    if export_format == 'pdf':
        return export_as_pdf(request, document, analysis)
    elif export_format == 'txt':
        return export_as_txt(document, analysis)
    elif export_format == 'csv':
        return export_as_csv(document, analysis)
    elif export_format == 'json':
        return export_as_json(document, analysis)
    
    return JsonResponse({'error': 'Export format not implemented'}, status=400)


def export_as_pdf(request, document, analysis):
    """Export analysis as PDF"""
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, spaceAfter=20)
    story.append(Paragraph(document.title or "Untitled", title_style))
    
    # Metadata
    if analysis:
        meta_data = f"Words: {analysis.word_count} | Keywords: {len(analysis.keywords or [])}"
        if analysis.publication_year:
            meta_data += f" | Year: {analysis.publication_year}"
        story.append(Paragraph(f"<i>{meta_data}</i>", styles['Italic']))
        story.append(Spacer(1, 20))
    
    # Abstract
    if analysis and analysis.abstract:
        story.append(Paragraph("Abstract", styles['Heading2']))
        story.append(Paragraph(analysis.abstract, styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Summary
    if analysis and analysis.summary:
        story.append(Paragraph("Summary", styles['Heading2']))
        story.append(Paragraph(analysis.summary, styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Keywords
    if analysis and analysis.keywords:
        story.append(Paragraph("Keywords", styles['Heading2']))
        story.append(Paragraph(", ".join(analysis.keywords), styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Methodology
    if analysis and analysis.methodology:
        story.append(Paragraph("Methodology", styles['Heading2']))
        for method in analysis.methodology:
            story.append(Paragraph(f"• {method}", styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Technologies
    if analysis and analysis.technologies:
        story.append(Paragraph("Technologies", styles['Heading2']))
        story.append(Paragraph(", ".join(analysis.technologies), styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Impact
    if analysis and analysis.impact:
        story.append(Paragraph("Impact & Contributions", styles['Heading2']))
        story.append(Paragraph(analysis.impact, styles['Normal']))
        story.append(Spacer(1, 15))
    
    doc.build(story)
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='application/pdf')


def export_as_txt(document, analysis):
    """Export analysis as text file with citation"""
    lines = []
    lines.append("=" * 60)
    lines.append(document.title or "Untitled Document")
    lines.append("=" * 60)
    lines.append("")

    # Citation block
    lines.append("CITATION")
    lines.append("-" * 40)
    authors = ", ".join(analysis.authors) if analysis and analysis.authors else "Unknown Author"
    year = analysis.publication_year if analysis and analysis.publication_year else "n.d."
    title = document.title or "Untitled"
    url = f" Retrieved from {document.url}" if document.url else ""
    lines.append(f"APA:     {authors} ({year}). {title}.{url}")
    lines.append(f"MLA:     {(analysis.authors[0] if analysis and analysis.authors else 'Unknown')}. \"{title}.\" {year}.{url}")
    lines.append(f"Chicago: {authors}. \"{title}.\" {year}.{url}")
    lines.append("")

    if analysis:
        if analysis.authors:
            lines.append(f"Authors: {', '.join(analysis.authors)}")
        if analysis.publication_year:
            lines.append(f"Publication Year: {analysis.publication_year}")
        lines.append(f"Word Count: {analysis.word_count}")
        lines.append("")

        if analysis.abstract:
            lines.append("ABSTRACT")
            lines.append("-" * 40)
            lines.append(analysis.abstract)
            lines.append("")

        if analysis.summary:
            lines.append("SUMMARY")
            lines.append("-" * 40)
            lines.append(analysis.summary)
            lines.append("")

        if analysis.keywords:
            lines.append("KEYWORDS")
            lines.append("-" * 40)
            lines.append(", ".join(analysis.keywords))
            lines.append("")

        if analysis.methodology:
            lines.append("METHODOLOGY")
            lines.append("-" * 40)
            for method in analysis.methodology:
                lines.append(f"• {method}")
            lines.append("")

        if analysis.technologies:
            lines.append("TECHNOLOGIES")
            lines.append("-" * 40)
            lines.append(", ".join(analysis.technologies))
            lines.append("")

        if analysis.impact:
            lines.append("IMPACT & CONTRIBUTIONS")
            lines.append("-" * 40)
            lines.append(analysis.impact)
            lines.append("")

        if analysis.goal:
            lines.append("RESEARCH GOAL")
            lines.append("-" * 40)
            lines.append(analysis.goal)
            lines.append("")

    content = "\n".join(lines)
    return HttpResponse(content, content_type='text/plain')


def export_as_csv(document, analysis):
    """Export analysis as CSV"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Field', 'Value'])
    writer.writerow(['Title', document.title or ''])
    
    if analysis:
        writer.writerow(['Authors', ', '.join(analysis.authors or [])])
        writer.writerow(['Publication Year', analysis.publication_year or ''])
        writer.writerow(['Word Count', analysis.word_count or 0])
        writer.writerow(['Abstract', analysis.abstract or ''])
        writer.writerow(['Summary', analysis.summary or ''])
        writer.writerow(['Keywords', ', '.join(analysis.keywords or [])])
        writer.writerow(['Methodology', ', '.join(analysis.methodology or [])])
        writer.writerow(['Technologies', ', '.join(analysis.technologies or [])])
        writer.writerow(['Goal', analysis.goal or ''])
        writer.writerow(['Impact', analysis.impact or ''])
    
    return HttpResponse(output.getvalue(), content_type='text/csv')


def export_as_json(document, analysis):
    """Export analysis as JSON with citation"""
    import json

    authors = analysis.authors if analysis and analysis.authors else []
    year = analysis.publication_year if analysis and analysis.publication_year else "n.d."
    title = document.title or "Untitled"
    url_str = document.url or ""
    author_str = ", ".join(authors) if authors else "Unknown Author"
    first_author = authors[0] if authors else "Unknown"

    data = {
        'title': document.title,
        'created_at': document.created_at.isoformat() if document.created_at else None,
        'citation': {
            'apa': f"{author_str} ({year}). {title}.{' Retrieved from ' + url_str if url_str else ''}",
            'mla': f"{first_author}. \"{title}.\" {year}.{' ' + url_str if url_str else ''}",
            'chicago': f"{author_str}. \"{title}.\" {year}.{' ' + url_str if url_str else ''}",
        },
    }

    if analysis:
        data.update({
            'authors': analysis.authors or [],
            'publication_year': analysis.publication_year,
            'abstract': analysis.abstract,
            'summary': analysis.summary,
            'keywords': analysis.keywords or [],
            'methodology': analysis.methodology or [],
            'technologies': analysis.technologies or [],
            'goal': analysis.goal,
            'impact': analysis.impact,
            'word_count': analysis.word_count,
            'references': analysis.references or [],
            'extracted_links': analysis.extracted_links or [],
        })

    return JsonResponse(data, json_dumps_params={'indent': 2})


@login_required
def submit_feedback(request, document_id):
    """Submit feedback on analysis"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    
    if request.method == 'POST':
        # TODO: Save feedback
        pass
    
    return JsonResponse({'success': True})


def health_check(request):
    """Health check endpoint"""
    return JsonResponse({'status': 'ok', 'version': '1.0'})


@login_required
def save_notes(request, document_id):
    """Save notes for a document"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        document.notes = notes
        document.save()
        return JsonResponse({'success': True, 'notes': notes})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required
def add_tag(request, document_id):
    """Add a tag to a document"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    
    if request.method == 'POST':
        new_tag = request.POST.get('tag', '').strip()
        if not new_tag:
            return JsonResponse({'success': False, 'error': 'Tag cannot be empty'}, status=400)
        
        current_tags = document.tags or []
        if new_tag not in current_tags:
            current_tags.append(new_tag)
            document.tags = current_tags
            document.save()
        
        return JsonResponse({'success': True, 'tags': current_tags})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required
def remove_tag(request, document_id):
    """Remove a tag from a document"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    
    if request.method == 'POST':
        tag = request.POST.get('tag', '').strip()
        current_tags = document.tags or []
        
        if tag in current_tags:
            current_tags.remove(tag)
            document.tags = current_tags
            document.save()
        
        return JsonResponse({'success': True, 'tags': current_tags})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@login_required
def similar_papers(request, document_id):
    """Find similar papers based on keywords and content"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    analysis = getattr(document, 'analysis', None)
    
    if not analysis or not analysis.keywords:
        return JsonResponse({'success': False, 'error': 'No keywords found'}, status=400)
    
    # Get keywords from current document
    keywords = analysis.keywords[:10]
    
    # Find other documents with similar keywords
    similar_docs = []
    user_docs = Document.objects.filter(user=request.user).exclude(id=document_id)
    
    for doc in user_docs:
        doc_analysis = getattr(doc, 'analysis', None)
        if doc_analysis and doc_analysis.keywords:
            # Calculate keyword overlap
            doc_keywords = set(doc_analysis.keywords[:10])
            current_keywords = set(keywords)
            overlap = len(doc_keywords.intersection(current_keywords))
            
            if overlap >= 2:
                similar_docs.append({
                    'id': doc.id,
                    'title': doc.title[:100],
                    'match_count': overlap,
                    'keywords': doc_analysis.keywords[:5],
                })
    
    # Sort by match count
    similar_docs.sort(key=lambda x: x['match_count'], reverse=True)
    
    return JsonResponse({
        'success': True,
        'similar': similar_docs[:5],
        'current_keywords': keywords
    })