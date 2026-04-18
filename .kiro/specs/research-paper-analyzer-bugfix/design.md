# Research Paper Analyzer Bugfix Design

## Overview

This document formalizes the fix approach for six interconnected bugs in the Django research paper analyzer. The bugs span four files: `rag_utils.py`, `nlp_processor.py`, `views.py`, and `paper_analyzer/settings.py`. Each bug has a distinct condition (C), expected correct behavior (P), and a set of behaviors that must be preserved (¬C). The fix strategy is minimal and surgical — change only what is broken, leave everything else untouched.

---

## Glossary

- **Bug_Condition (C)**: The specific input or code path that triggers a defect.
- **Property (P)**: The correct behavior the fixed code must exhibit when C holds.
- **Preservation**: Existing behaviors that must remain unchanged after the fix.
- **`analyze_text_with_groq`**: Function in `analyzer/rag_utils.py` that calls the Groq LLM and returns a plain `str`.
- **`rag_pipeline`**: Function in `analyzer/rag_utils.py` that returns `{"summary": "..."}` (a `dict`).
- **`analyze_document`**: View in `analyzer/views.py` that calls `analyze_text_with_groq` and then calls `.get()` on the result.
- **`ask_question`**: View in `analyzer/views.py` that calls `rag_pipeline` and passes the raw return value as `answer`.
- **`EnhancedNLPProcessor`**: Class in `analyzer/nlp_processor.py` whose module-level imports crash the server when NLTK data is absent.
- **`AuthenticationForm`**: Django's built-in login form that authenticates by `username`, not `email`.
- **`EmailOrUsernameModelBackend`**: Custom backend in `analyzer/backends.py` that can authenticate by email — but is bypassed by `AuthenticationForm`.
- **`EMAIL_USE_TLS` / `EMAIL_USE_SSL`**: Django SMTP settings; port 465 requires `EMAIL_USE_SSL=True`, not `EMAIL_USE_TLS=True`.
- **`MLProcessor`**: Class in `analyzer/ml_model.py` that has no `extract_links` or `extract_references` methods.

---

## Bug Details

### Bug 1 — `analyze_text_with_groq` Returns String, View Calls `.get()` on It

#### Bug Condition

The bug manifests whenever `analyze_document` calls `analyze_text_with_groq(content)`. The function returns a plain `str`, but the view immediately calls `.get('summary', '')` on the result, which is a `str` method that does not exist — causing an `AttributeError` or silently returning empty strings for all analysis fields.

**Formal Specification:**
```
FUNCTION isBugCondition_1(call_result)
  INPUT: call_result — the return value of analyze_text_with_groq(content)
  OUTPUT: boolean

  RETURN isinstance(call_result, str)
         AND views.analyze_document calls call_result.get('summary', '')
END FUNCTION
```

**Examples:**
- User uploads a PDF → `analyze_text_with_groq` returns `"Here is the summary..."` → `"Here is the summary...".get('summary', '')` raises `AttributeError`.
- The `isinstance(analysis_data, str)` safety guard in `analyze_document` catches this and wraps it, but only populates `summary` — all other fields (`abstract`, `keywords`, `methodology`, etc.) are empty.

---

### Bug 2 — `nlp_processor.py` Module-Level NLTK Imports Crash Server on Startup

#### Bug Condition

The bug manifests when the Django server starts and NLTK punkt/stopwords data is not present on the host. `nlp_processor.py` executes `from nltk.tokenize import sent_tokenize, word_tokenize` and `from nltk.corpus import stopwords` at module level, and calls `nltk.download()` at module level. If NLTK data is missing and the download fails (e.g., no network, restricted environment), the import raises a `LookupError` or `OSError`, preventing the server from booting.

**Formal Specification:**
```
FUNCTION isBugCondition_2(environment)
  INPUT: environment — the host where Django starts
  OUTPUT: boolean

  RETURN nltk_punkt_data_present(environment) == False
         OR nltk_stopwords_data_present(environment) == False
         AND nlp_processor module is imported at startup
END FUNCTION
```

**Examples:**
- Fresh deployment without NLTK data → server fails to start with `LookupError: Resource punkt not found`.
- Restricted network environment → `nltk.download()` at module level hangs or raises `OSError`.

---

### Bug 3 — Login Form Uses `AuthenticationForm` but Users Registered with Email as Username

#### Bug Condition

The bug manifests when a registered user attempts to log in. `CustomRegistrationForm.save()` sets `user.username = self.cleaned_data['email']`, so the stored username is an email address. The `login_view` uses `AuthenticationForm`, which internally calls `authenticate(username=..., password=...)` using Django's default backend — not `EmailOrUsernameModelBackend`. The default backend does a case-sensitive `username` lookup, which may fail if the user types their email in a different case, and the form label says "Username" rather than "Email", confusing users.

**Formal Specification:**
```
FUNCTION isBugCondition_3(login_attempt)
  INPUT: login_attempt — a POST to login_view with {username_field: email, password: pwd}
  OUTPUT: boolean

  RETURN login_attempt.form_class == AuthenticationForm
         AND user.username == user.email  (set during registration)
         AND AuthenticationForm uses default Django backend (not EmailOrUsernameModelBackend)
END FUNCTION
```

**Examples:**
- User registers with `alice@example.com` → `user.username = "alice@example.com"`.
- User sees "Username" label on login form, types `Alice@Example.com` → default backend does case-sensitive match → login fails.
- Even with correct case, the form label misleads users who expect an "Email" field.

---

### Bug 4 — Email Config Uses Port 465 with `EMAIL_USE_TLS=True`

#### Bug Condition

The bug manifests when the application attempts to send an OTP email. `settings.py` sets `EMAIL_PORT=465` and `EMAIL_USE_TLS=True`. Port 465 uses implicit SSL (the connection is wrapped in SSL from the start), which requires `EMAIL_USE_SSL=True`. `EMAIL_USE_TLS=True` is for STARTTLS on port 587, where the connection starts unencrypted and upgrades. Using STARTTLS on port 465 causes an SSL handshake error.

**Formal Specification:**
```
FUNCTION isBugCondition_4(smtp_config)
  INPUT: smtp_config — Django email settings dict
  OUTPUT: boolean

  RETURN smtp_config['EMAIL_PORT'] == 465
         AND smtp_config['EMAIL_USE_TLS'] == True
         AND smtp_config['EMAIL_USE_SSL'] != True
END FUNCTION
```

**Examples:**
- User requests password reset → `create_and_send_otp` calls Django's `send_mail` → SMTP connection to `smtp.gmail.com:465` with STARTTLS → `ssl.SSLError: wrong version number` or `ConnectionRefusedError`.

---

### Bug 5 — `analyze_document` Calls Non-Existent `extract_links` / `extract_references` on `MLProcessor`

#### Bug Condition

The bug manifests when `analyze_document` saves an `AnalysisResult`. It calls:
```python
extracted_links=getattr(ml_processor, 'extract_links', lambda x: [])(content),
references=getattr(ml_processor, 'extract_references', lambda x: [])(content),
```
`MLProcessor` has no `extract_links` or `extract_references` methods. The `getattr` fallback silently returns `[]` for both fields every time, so links and references are never extracted.

**Formal Specification:**
```
FUNCTION isBugCondition_5(ml_processor_instance)
  INPUT: ml_processor_instance — the MLProcessor object
  OUTPUT: boolean

  RETURN hasattr(ml_processor_instance, 'extract_links') == False
         AND hasattr(ml_processor_instance, 'extract_references') == False
END FUNCTION
```

**Examples:**
- Any document analysis → `extracted_links` is always `[]`, `references` is always `[]`.

---

### Bug 6 — `ask_question` Returns `{"answer": {"summary": "..."}}` Instead of Plain String

#### Bug Condition

The bug manifests when a user asks a question about a document. `rag_pipeline` returns `{"summary": "..."}` (a dict). The `ask_question` view passes this dict directly as the `answer` value in `JsonResponse({'answer': answer})`, so the frontend receives `{"answer": {"summary": "..."}}` instead of `{"answer": "..."}`.

**Formal Specification:**
```
FUNCTION isBugCondition_6(rag_pipeline_result)
  INPUT: rag_pipeline_result — return value of rag_pipeline(content, question)
  OUTPUT: boolean

  RETURN isinstance(rag_pipeline_result, dict)
         AND 'summary' in rag_pipeline_result
         AND ask_question view passes rag_pipeline_result directly as answer
END FUNCTION
```

**Examples:**
- User asks "What is the methodology?" → `rag_pipeline` returns `{"summary": "The methodology is..."}` → frontend receives `{"answer": {"summary": "The methodology is..."}}` → frontend JS fails to render the answer string.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Dashboard, library, and result pages continue to render correctly with existing data.
- PDF text extraction via `pdf_processor` is unaffected.
- Contact form saves messages to the database and returns success.
- Compare papers endpoint returns similarity scores and common keywords/methods.
- Export (PDF, TXT, CSV, JSON) continues to generate correct file formats.
- Rate limit middleware continues to enforce 30 req/60s per IP on `/analyze/` and `/contact/`.
- Document deletion continues to work and return success JSON.
- New user registration continues to create accounts, log users in, and redirect to dashboard.
- All existing `MLProcessor` methods (`extract_authors`, `extract_keywords`, `detect_methodology`, etc.) are unchanged.

**Scope:**
All code paths that do NOT involve the six bug conditions above must be completely unaffected by these fixes. This includes:
- All views other than `login_view`, `analyze_document`, and `ask_question`.
- All `MLProcessor` methods other than the two being added.
- All settings other than the email SSL/TLS configuration.

---

## Hypothesized Root Cause

### Bug 1 — Type Mismatch
`analyze_text_with_groq` was originally designed to return a plain string (a simple Groq completion), but `analyze_document` was written expecting a dict (like the commented-out version of the function that returned `json.loads(...)` output). The function was later simplified to return a string, but the view was never updated to match.

### Bug 2 — Eager Module-Level Imports
`nlp_processor.py` was written with top-level `import nltk` and `from nltk.tokenize import ...` statements, plus module-level `nltk.download()` calls. This is a common anti-pattern in Django apps deployed to environments where NLTK data may not be pre-installed. `ml_model.py` already demonstrates the correct lazy-loading pattern (`_load_nltk()`) but `nlp_processor.py` was not updated to match.

### Bug 3 — Form/Backend Mismatch
`AuthenticationForm` is Django's default form and uses the default authentication backend. The custom `EmailOrUsernameModelBackend` is registered in `AUTHENTICATION_BACKENDS` but `AuthenticationForm.authenticate()` calls `authenticate()` without specifying a backend, so Django tries all backends in order. The issue is that `AuthenticationForm` passes the field value as `username=`, and while `EmailOrUsernameModelBackend` handles this correctly, the form label still says "Username" — misleading users who registered with email. The fix is to replace `AuthenticationForm` with a custom form that labels the field "Email".

### Bug 4 — Wrong TLS Setting for Port 465
Port 465 (SMTPS) uses implicit SSL — the entire connection is SSL-wrapped from the start. `EMAIL_USE_SSL=True` tells Django to use `smtplib.SMTP_SSL`. `EMAIL_USE_TLS=True` tells Django to use `smtplib.SMTP` with `.starttls()`, which is for port 587. Using STARTTLS on port 465 fails because the server expects an SSL handshake immediately, not a STARTTLS upgrade.

### Bug 5 — Missing Methods on MLProcessor
`extract_links` and `extract_references` were referenced in `views.py` but never implemented in `ml_model.py`. The `getattr` fallback silently masks the absence, so no error is raised — but the data is never populated.

### Bug 6 — View Passes Dict Instead of Extracting String
`rag_pipeline` was refactored to return `{"summary": "..."}` for consistency with other pipeline functions, but `ask_question` was not updated to extract the string value. The view passes the entire dict as `answer`.

---

## Correctness Properties

Property 1: Bug Condition — `analyze_text_with_groq` Returns a Dict

_For any_ call to `analyze_text_with_groq(content)` where `content` is a non-empty string, the fixed function SHALL return a `dict` with at least the key `"summary"`, so that `analysis_data.get('summary', '')` and all other `.get()` calls in `analyze_document` succeed and return meaningful values.

**Validates: Requirements 2.1**

Property 2: Bug Condition — `nlp_processor.py` Imports Without Crashing

_For any_ Django startup environment where NLTK punkt or stopwords data is absent, importing `analyzer.nlp_processor` SHALL NOT raise a `LookupError`, `OSError`, or any other exception. All NLTK initialization SHALL be deferred to lazy-load functions called only when NLP processing is actually invoked.

**Validates: Requirements 2.2**

Property 3: Bug Condition — Login Succeeds with Email and Password

_For any_ user who registered via `CustomRegistrationForm` (where `username == email`), submitting the login form with their email and correct password SHALL authenticate the user and redirect to the dashboard. The login form SHALL display "Email" as the field label.

**Validates: Requirements 2.3**

Property 4: Bug Condition — OTP Email Sends Successfully on Port 465

_For any_ password reset request where `EMAIL_PORT=465`, the SMTP connection SHALL use implicit SSL (`EMAIL_USE_SSL=True`, `EMAIL_USE_TLS=False`), and the OTP email SHALL be delivered without an SSL handshake error.

**Validates: Requirements 2.4**

Property 5: Bug Condition — `extract_links` and `extract_references` Return Real Data

_For any_ call to `analyze_document` that saves an `AnalysisResult`, the `extracted_links` and `references` fields SHALL be populated by real extraction logic (or gracefully return `[]` via implemented methods), not by a `getattr` fallback to a missing method.

**Validates: Requirements 2.5**

Property 6: Bug Condition — `ask_question` Returns Plain String Answer

_For any_ POST to `ask_question` with a valid question, the `JsonResponse` SHALL contain `{"answer": "<string>"}` where the value is a plain string, not a nested dict.

**Validates: Requirements 2.6**

Property 7: Preservation — All Non-Buggy Code Paths Unchanged

_For any_ request that does NOT exercise the six bug conditions above (dashboard, library, compare, export, contact, delete, register, plagiarism check, PDF extraction), the fixed code SHALL produce exactly the same behavior as the original code.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

---

## Fix Implementation

### Bug 1 Fix — `analyzer/rag_utils.py`: `analyze_text_with_groq`

**File**: `analyzer/rag_utils.py`  
**Function**: `analyze_text_with_groq`

**Specific Changes:**
1. Change the return type from `str` to `dict`.
2. Ask the Groq LLM to return a structured JSON response with keys: `summary`, `abstract`, `keywords`, `methodology`, `technologies`, `goal`, `impact`, `publication_year`, `authors`, `research_gaps`, `conclusion`.
3. Parse the LLM response with `json.loads()`, stripping any markdown code fences.
4. On `json.JSONDecodeError`, fall back to `{"summary": raw_content, "abstract": "", "keywords": [], ...}` so `.get()` calls always succeed.
5. On any exception, return `{"summary": f"Error: {str(e)}", ...}` — never a plain string.

```
FUNCTION analyze_text_with_groq(text, prompt)
  INPUT: text: str, prompt: str
  OUTPUT: dict with keys summary, abstract, keywords, methodology,
          technologies, goal, impact, publication_year, authors,
          research_gaps, conclusion, statistics

  response_str := call_groq_llm(text, prompt, system="Return only valid JSON")
  TRY
    data := json.loads(strip_markdown_fences(response_str))
    data['statistics'] := {word_count: len(text.split()), unique_words: ...}
    RETURN data
  CATCH json.JSONDecodeError
    RETURN {summary: response_str[:1000], abstract: "", keywords: [], ...}
  CATCH Exception as e
    RETURN {summary: f"Error: {e}", abstract: "", keywords: [], ...}
END FUNCTION
```

---

### Bug 2 Fix — `analyzer/nlp_processor.py`: Lazy NLTK Loading

**File**: `analyzer/nlp_processor.py`  
**Class**: `EnhancedNLPProcessor`

**Specific Changes:**
1. Remove all module-level `import nltk`, `from nltk.tokenize import ...`, `from nltk.corpus import stopwords`, and `nltk.download()` calls.
2. Add a module-level `_load_nltk()` lazy function (mirroring the pattern already in `ml_model.py`) that imports and downloads NLTK data only on first call, with a `try/except` fallback to regex-based alternatives.
3. In `EnhancedNLPProcessor.__init__`, remove `self.stop_words = set(stopwords.words('english'))` — replace with a lazy property that calls `_load_nltk()`.
4. In all methods that use `sent_tokenize`, `word_tokenize`, or `stopwords`, call `_load_nltk()` first and use the lazily loaded references (or regex fallback if NLTK is unavailable).

```
MODULE-LEVEL:
  _nltk_available = None
  _sent_tokenize = None
  _word_tokenize = None
  _stopwords_set = None

FUNCTION _load_nltk()
  IF _nltk_available is not None: RETURN _nltk_available
  TRY
    import nltk
    download punkt and stopwords if missing
    set _sent_tokenize, _word_tokenize, _stopwords_set
    _nltk_available = True
  CATCH Exception
    _nltk_available = False
    set fallback regex-based alternatives
  RETURN _nltk_available
```

---

### Bug 3 Fix — `analyzer/views.py`: Replace `AuthenticationForm` with Email-Based Login Form

**File**: `analyzer/views.py`  
**Function**: `login_view`

**Specific Changes:**
1. Replace `AuthenticationForm` with a custom `EmailLoginForm` (defined in `analyzer/forms.py`) that has an `email` field (not `username`) and a `password` field.
2. In `EmailLoginForm.clean()`, call `authenticate(request, username=email, password=password)` — this routes through `EmailOrUsernameModelBackend` which already handles email lookup correctly.
3. Update `login_view` to use `EmailLoginForm` instead of `AuthenticationForm`.
4. Remove the `from django.contrib.auth.forms import AuthenticationForm` import from `views.py` (or keep it only if used elsewhere).

```
CLASS EmailLoginForm(forms.Form):
  email = EmailField(label="Email", ...)
  password = CharField(widget=PasswordInput, ...)

  FUNCTION clean(self):
    email = self.cleaned_data.get('email')
    password = self.cleaned_data.get('password')
    user = authenticate(request=self.request, username=email, password=password)
    IF user is None:
      RAISE ValidationError("Invalid email or password.")
    self.user_cache = user
    RETURN self.cleaned_data

  FUNCTION get_user(self): RETURN self.user_cache
```

---

### Bug 4 Fix — `paper_analyzer/settings.py`: Correct SMTP SSL Settings

**File**: `paper_analyzer/settings.py`

**Specific Changes:**
1. Change `EMAIL_USE_TLS` default from `'True'` to `'False'`.
2. Add `EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True').lower() == 'true'`.
3. This makes port 465 work correctly with implicit SSL. If operators want to use port 587 instead, they set `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`, `EMAIL_USE_SSL=False` via environment variables.

```
EMAIL_PORT     = int(os.getenv('EMAIL_PORT', 465))
EMAIL_USE_TLS  = os.getenv('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_USE_SSL  = os.getenv('EMAIL_USE_SSL', 'True').lower() == 'true'
```

---

### Bug 5 Fix — `analyzer/ml_model.py`: Add `extract_links` and `extract_references`

**File**: `analyzer/ml_model.py`  
**Class**: `MLProcessor`

**Specific Changes:**
1. Add `extract_links(self, text: str) -> List[str]` — uses regex to find all `http(s)://` URLs in the text.
2. Add `extract_references(self, text: str) -> List[str]` — extracts the References/Bibliography section and splits it into individual reference strings.
3. Both methods return `[]` gracefully if no matches are found.

```
FUNCTION extract_links(self, text: str) -> List[str]:
  RETURN re.findall(r'https?://[^\s\)\]>,"]+', text)[:50]

FUNCTION extract_references(self, text: str) -> List[str]:
  ref_section := extract text after "References" or "Bibliography" heading
  IF ref_section is empty: RETURN []
  RETURN split ref_section into individual numbered/bulleted entries[:100]
```

---

### Bug 6 Fix — `analyzer/views.py`: `ask_question` Extracts String from `rag_pipeline` Result

**File**: `analyzer/views.py`  
**Function**: `ask_question`

**Specific Changes:**
1. After calling `answer = rag_pipeline(document.content, question)`, check if `answer` is a `dict`.
2. If so, extract `answer.get('summary', str(answer))` to get the plain string.
3. Return `JsonResponse({'success': True, 'question': question, 'answer': answer_string})`.

```
answer = rag_pipeline(document.content, question)
IF isinstance(answer, dict):
  answer = answer.get('summary', str(answer))
RETURN JsonResponse({'success': True, 'question': question, 'answer': answer})
```

---

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, write exploratory tests that demonstrate each bug on the **unfixed** code to confirm root cause analysis; then write fix-checking and preservation tests to verify the fixes are correct and regressions are absent.

---

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate each bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Cases:**

1. **Bug 1 — String Return Type**: Call `analyze_text_with_groq("some text")` and assert `isinstance(result, dict)` → will fail on unfixed code (returns `str`).
2. **Bug 2 — Module Import Crash**: In a test environment without NLTK data, `import analyzer.nlp_processor` → will raise `LookupError` on unfixed code.
3. **Bug 3 — Login with Email**: Register a user with email, then POST to `login_view` with that email → will fail or show wrong label on unfixed code.
4. **Bug 4 — SMTP SSL Config**: Assert `settings.EMAIL_USE_SSL == True` and `settings.EMAIL_USE_TLS == False` when `EMAIL_PORT == 465` → will fail on unfixed code.
5. **Bug 5 — Missing Methods**: Assert `hasattr(ml_processor, 'extract_links')` and `hasattr(ml_processor, 'extract_references')` → will fail on unfixed code.
6. **Bug 6 — Nested Dict Answer**: Call `ask_question` view and assert `isinstance(response_json['answer'], str)` → will fail on unfixed code (returns dict).

**Expected Counterexamples:**
- `analyze_text_with_groq` returns `str`, not `dict`.
- `nlp_processor` import raises `LookupError` when NLTK data absent.
- Login form field label is "Username", not "Email".
- `EMAIL_USE_SSL` is not set; `EMAIL_USE_TLS=True` with port 465.
- `ml_processor` has no `extract_links` or `extract_references` attributes.
- `ask_question` response body is `{"answer": {"summary": "..."}}`.

---

### Fix Checking

**Goal**: Verify that for all inputs where each bug condition holds, the fixed code produces the expected behavior.

**Pseudocode:**
```
FOR ALL content WHERE isBugCondition_1(analyze_text_with_groq(content)) DO
  result := analyze_text_with_groq_fixed(content)
  ASSERT isinstance(result, dict)
  ASSERT 'summary' in result
END FOR

FOR ALL environment WHERE isBugCondition_2(environment) DO
  ASSERT import analyzer.nlp_processor does NOT raise
END FOR

FOR ALL login_attempt WHERE isBugCondition_3(login_attempt) DO
  result := login_view_fixed(login_attempt)
  ASSERT result.status_code == 302  # redirect to dashboard
  ASSERT login_attempt.user.is_authenticated
END FOR

FOR ALL smtp_config WHERE isBugCondition_4(smtp_config) DO
  ASSERT smtp_config['EMAIL_USE_SSL'] == True
  ASSERT smtp_config['EMAIL_USE_TLS'] == False
END FOR

FOR ALL ml_processor WHERE isBugCondition_5(ml_processor) DO
  ASSERT hasattr(ml_processor, 'extract_links')
  ASSERT hasattr(ml_processor, 'extract_references')
  ASSERT isinstance(ml_processor.extract_links(text), list)
  ASSERT isinstance(ml_processor.extract_references(text), list)
END FOR

FOR ALL question_request WHERE isBugCondition_6(rag_pipeline(content, question)) DO
  response := ask_question_fixed(question_request)
  ASSERT isinstance(response.json()['answer'], str)
END FOR
```

---

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed code produces the same behavior as the original code.

**Pseudocode:**
```
FOR ALL request WHERE NOT any isBugCondition(request) DO
  ASSERT fixed_view(request) == original_view(request)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because it generates many test cases automatically and catches edge cases that manual tests miss.

**Test Cases:**
1. **Dashboard Preservation**: Authenticated GET to `/dashboard/` returns 200 with correct context — unchanged.
2. **PDF Extraction Preservation**: Upload a valid PDF → text extraction succeeds — unchanged.
3. **Contact Form Preservation**: POST to `/contact/` with valid data → `ContactMessage` saved, 200 JSON success — unchanged.
4. **Compare Papers Preservation**: GET `/compare/<id1>/<id2>/` → returns similarity JSON — unchanged.
5. **Export Preservation**: GET `/export/<id>/pdf/` → returns PDF file — unchanged.
6. **Delete Document Preservation**: POST `/delete/<id>/` → document deleted, success JSON — unchanged.
7. **Registration Preservation**: POST to `/register/` with new email → user created, logged in, redirected — unchanged.
8. **MLProcessor Existing Methods**: `ml_processor.extract_keywords(text)`, `ml_processor.detect_methodology(text)`, etc. return same results — unchanged.

---

### Unit Tests

- Test `analyze_text_with_groq` returns a `dict` with all expected keys (mock Groq client).
- Test `analyze_text_with_groq` handles `json.JSONDecodeError` gracefully and still returns a `dict`.
- Test `nlp_processor.py` can be imported without NLTK data present (mock NLTK as unavailable).
- Test `EnhancedNLPProcessor.generate_summary` works with NLTK unavailable (regex fallback).
- Test `EmailLoginForm` with valid email/password authenticates correctly.
- Test `EmailLoginForm` with wrong password raises `ValidationError`.
- Test `settings.EMAIL_USE_SSL=True` and `EMAIL_USE_TLS=False` when `EMAIL_PORT=465`.
- Test `ml_processor.extract_links` returns a list of URLs from text containing URLs.
- Test `ml_processor.extract_references` returns a list of reference strings from text with a References section.
- Test `ask_question` view returns `{"answer": str}` when `rag_pipeline` returns a dict.

---

### Property-Based Tests

- Generate random non-empty strings as `content` → `analyze_text_with_groq(content)` always returns a `dict` (mock Groq to return various string formats including invalid JSON).
- Generate random text inputs → `EnhancedNLPProcessor` methods never raise on import or call, regardless of NLTK availability.
- Generate random email/password pairs → `EmailLoginForm` never raises an unhandled exception (only `ValidationError` for invalid credentials).
- Generate random text with varying URL patterns → `extract_links` always returns a `list` (never raises).
- Generate random text with varying reference section formats → `extract_references` always returns a `list`.
- Generate random `rag_pipeline` return values (dict or str) → `ask_question` always returns `{"answer": str}`.

---

### Integration Tests

- Full document analysis flow: upload PDF → `analyze_document` → `AnalysisResult` saved with non-empty `summary`, `keywords`, `methodology` fields.
- Full login flow: register with email → log out → log in with same email → redirected to dashboard.
- Full OTP flow: request password reset → OTP email sent (mock SMTP) → verify OTP → reset password → log in with new password.
- Full Q&A flow: upload document → ask question → receive plain string answer in JSON response.
- Server startup test: start Django with NLTK data absent → server boots without error → NLP endpoints work with regex fallback.
