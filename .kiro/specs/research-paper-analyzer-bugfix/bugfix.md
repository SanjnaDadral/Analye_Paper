# Bugfix Requirements Document

## Introduction

The research paper analyzer Django application has several interconnected bugs that prevent it from working correctly. The most critical is that `analyze_text_with_groq()` in `rag_utils.py` returns a plain string, but `views.py` calls `.get()` on it as if it were a dictionary — causing every document analysis to silently fall through to the fallback ML path or crash. Additionally, `nlp_processor.py` imports NLTK at module level (not lazily), which can crash the server on startup when NLTK data is missing. The login form uses Django's `AuthenticationForm` (which expects a `username` field), but registration saves `email` as the `username` — so users who register can never log in through the standard form. Finally, the email configuration uses port 465 with `EMAIL_USE_TLS=True`, which is incorrect (port 465 requires SSL, not STARTTLS), breaking password-reset OTP delivery.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user uploads a PDF or URL for analysis THEN the system calls `analyze_text_with_groq(content)` which returns a plain string, and then calls `.get('summary', '')` on that string, causing a `AttributeError` or silently returning empty analysis fields for every document.

1.2 WHEN the Django application starts and NLTK punkt/stopwords data is not present THEN `nlp_processor.py` crashes at import time because it calls `nltk.download()` at module level, preventing the server from booting.

1.3 WHEN a user registers with their email address THEN the system saves `email` as the `username` field, but WHEN that user tries to log in using the `AuthenticationForm` THEN the form's `username` label prompts for a username (not email), and the `EmailOrUsernameModelBackend` is bypassed by `AuthenticationForm`'s internal `authenticate()` call which does not pass the custom backend — causing login to fail for registered users.

1.4 WHEN a user requests a password reset OTP THEN the system attempts to send email via SMTP port 465 with `EMAIL_USE_TLS=True` (STARTTLS), but port 465 requires `EMAIL_USE_SSL=True` instead, causing all OTP emails to fail with an SSL/TLS handshake error.

1.5 WHEN the `analyze_document` view saves an `AnalysisResult` THEN it calls `getattr(ml_processor, 'extract_links', lambda x: [])(content)` and `getattr(ml_processor, 'extract_references', lambda x: [])(content)`, but `MLProcessor` has no `extract_links` or `extract_references` methods, so these always silently return empty lists instead of actual extracted data.

1.6 WHEN the `rag_pipeline` function in `rag_utils.py` is called from `ask_question` view THEN it returns `{"summary": "..."}` (a dict with a `summary` key), but the view returns `answer` directly in `JsonResponse({'answer': answer})` — so the frontend receives `{"answer": {"summary": "..."}}` instead of a plain answer string.

### Expected Behavior (Correct)

2.1 WHEN a user uploads a PDF or URL for analysis THEN the system SHALL call `analyze_text_with_groq(content)` and receive a properly structured dictionary with keys like `summary`, `abstract`, `keywords`, etc., so that `.get()` calls succeed and analysis fields are populated correctly.

2.2 WHEN the Django application starts THEN the system SHALL import `nlp_processor.py` without executing any NLTK downloads at module level, deferring all NLTK initialization to lazy-load functions that run only when NLP processing is actually needed.

2.3 WHEN a user who registered with their email tries to log in THEN the system SHALL present a login form with an "Email" label (not "Username"), authenticate using the `EmailOrUsernameModelBackend` correctly, and successfully log the user in with their email and password.

2.4 WHEN a user requests a password reset OTP THEN the system SHALL send the OTP email successfully by using the correct SMTP configuration: port 465 with `EMAIL_USE_SSL=True` and `EMAIL_USE_TLS=False`, or port 587 with `EMAIL_USE_TLS=True`.

2.5 WHEN the `analyze_document` view saves an `AnalysisResult` THEN the system SHALL correctly extract links and references from the document content using properly implemented methods on `MLProcessor`, or store empty lists gracefully without relying on non-existent methods.

2.6 WHEN the `ask_question` view calls `rag_pipeline` and returns the answer THEN the system SHALL return a plain string answer in `JsonResponse({'answer': answer_string})` so the frontend receives the answer text directly.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN an authenticated user accesses the dashboard, library, or result pages THEN the system SHALL CONTINUE TO render those pages correctly with their existing data.

3.2 WHEN a user uploads a valid PDF file THEN the system SHALL CONTINUE TO extract text from the PDF using the existing `pdf_processor` pipeline without changes.

3.3 WHEN a user submits the contact form THEN the system SHALL CONTINUE TO save the contact message to the database and return a success response.

3.4 WHEN a user accesses the compare papers endpoint with two valid document IDs THEN the system SHALL CONTINUE TO return the comparison JSON with similarity scores and common keywords/methods.

3.5 WHEN a user exports a document in PDF, TXT, CSV, or JSON format THEN the system SHALL CONTINUE TO generate and return the correct file format.

3.6 WHEN the rate limit middleware processes requests to `/analyze/` or `/contact/` THEN the system SHALL CONTINUE TO enforce the 30 requests per 60 seconds limit per IP address.

3.7 WHEN a user deletes a document THEN the system SHALL CONTINUE TO delete the document and return a success JSON response.

3.8 WHEN a new user registers with a unique email THEN the system SHALL CONTINUE TO create the account, log them in, and redirect to the dashboard.
