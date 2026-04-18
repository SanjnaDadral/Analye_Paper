# Implementation Plan

- [x] 1. Write bug condition exploration tests
  - **Property 1: Bug Condition** - Six Bug Conditions Across Four Files
  - **CRITICAL**: These tests MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **NOTE**: These tests encode the expected behavior — they will validate the fixes when they pass after implementation
  - **GOAL**: Surface counterexamples that demonstrate each bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope each property to the concrete failing case(s) to ensure reproducibility
  - Write test for Bug 1: call `analyze_text_with_groq("some text")` and assert `isinstance(result, dict)` — will FAIL (returns `str`)
  - Write test for Bug 2: in an environment without NLTK data, assert `import analyzer.nlp_processor` does NOT raise — will FAIL (`LookupError`)
  - Write test for Bug 3: register a user with email, POST to `login_view` with that email, assert redirect to dashboard — will FAIL (wrong form/label)
  - Write test for Bug 4: assert `settings.EMAIL_USE_SSL == True` and `settings.EMAIL_USE_TLS == False` when `EMAIL_PORT == 465` — will FAIL
  - Write test for Bug 5: assert `hasattr(ml_processor, 'extract_links')` and `hasattr(ml_processor, 'extract_references')` — will FAIL
  - Write test for Bug 6: call `ask_question` view and assert `isinstance(response.json()['answer'], str)` — will FAIL (returns nested dict)
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: All tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found:
    - `analyze_text_with_groq` returns `str`, not `dict`
    - `nlp_processor` import raises `LookupError` when NLTK data absent
    - Login form field label is "Username", not "Email"; `AuthenticationForm` bypasses `EmailOrUsernameModelBackend`
    - `EMAIL_USE_SSL` is not set; `EMAIL_USE_TLS=True` with port 465 causes SSL handshake error
    - `ml_processor` has no `extract_links` or `extract_references` attributes
    - `ask_question` response body is `{"answer": {"summary": "..."}}` instead of `{"answer": "..."}`
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Buggy Code Paths Remain Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for all non-buggy inputs (requests that do NOT exercise the six bug conditions)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Observe: authenticated GET to `/dashboard/` returns 200 with correct context
  - Observe: valid PDF upload → `pdf_processor` extracts text successfully
  - Observe: POST to `/contact/` with valid data → `ContactMessage` saved, JSON success returned
  - Observe: `ml_processor.extract_keywords(text)`, `ml_processor.detect_methodology(text)` return lists (existing methods unchanged)
  - Observe: POST to `/register/` with new email → user created, logged in, redirected to dashboard
  - Observe: document deletion returns success JSON
  - Write property-based test: for all authenticated requests to dashboard/library/result pages, response status is 200
  - Write property-based test: for all valid PDF uploads, `pdf_processor.extract_text` returns `{'success': True, 'text': <non-empty str>}`
  - Write property-based test: for all existing `MLProcessor` methods, return type is unchanged (list or str as appropriate)
  - Verify all preservation tests PASS on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 3. Fix Bug 1 — `analyze_text_with_groq` returns string, view calls `.get()` on it

  - [x] 3.1 Implement the fix in `analyzer/rag_utils.py`
    - Change `analyze_text_with_groq` to ask the Groq LLM for a structured JSON response with keys: `summary`, `abstract`, `keywords`, `methodology`, `technologies`, `goal`, `impact`, `publication_year`, `authors`, `research_gaps`, `conclusion`
    - Add system prompt: `"Return only valid JSON object, no markdown formatting."`
    - Parse the LLM response with `json.loads()`, stripping any markdown code fences (` ```json ` / ` ``` `)
    - Add `statistics` key: `{"word_count": len(text.split()), "unique_words": len(set(text.split()))}`
    - On `json.JSONDecodeError`, fall back to `{"summary": raw_content[:1000], "abstract": "", "keywords": [], "methodology": [], "technologies": [], "goal": "", "impact": "", "publication_year": "", "authors": [], "research_gaps": [], "conclusion": "", "statistics": {...}}`
    - On any other exception, return the same safe dict structure with `"summary": f"Error: {str(e)}"`
    - Never return a plain `str` — always return a `dict`
    - _Bug_Condition: isBugCondition_1(result) where isinstance(result, str) AND views.py calls result.get('summary', '')_
    - _Expected_Behavior: isinstance(result, dict) AND 'summary' in result AND all .get() calls in analyze_document succeed_
    - _Preservation: rag_pipeline function and ask_question view are NOT modified in this task_
    - _Requirements: 2.1_

  - [x] 3.2 Verify Bug 1 exploration test now passes
    - **Property 1: Expected Behavior** - `analyze_text_with_groq` Returns Dict
    - **IMPORTANT**: Re-run the SAME test from task 1 for Bug 1 — do NOT write a new test
    - Run: call `analyze_text_with_groq("some text")` and assert `isinstance(result, dict)` with key `"summary"`
    - **EXPECTED OUTCOME**: Test PASSES (confirms Bug 1 is fixed)
    - _Requirements: 2.1_

  - [x] 3.3 Verify preservation tests still pass after Bug 1 fix
    - **Property 2: Preservation** - Non-Buggy Code Paths Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Confirm `rag_pipeline` still returns `{"summary": "..."}` (unchanged)
    - Confirm `analyze_document` fallback ML path still works when Groq raises an exception
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 4. Fix Bug 2 — `nlp_processor.py` module-level NLTK imports crash server on startup

  - [x] 4.1 Implement the fix in `analyzer/nlp_processor.py`
    - Remove all module-level `import nltk`, `from nltk.tokenize import sent_tokenize, word_tokenize`, `from nltk.corpus import stopwords`, and `nltk.download()` calls
    - Add module-level lazy-load state variables: `_nltk_available = None`, `_sent_tokenize = None`, `_word_tokenize = None`, `_stopwords_set = None`
    - Add `_load_nltk()` function (mirroring the pattern in `ml_model.py`): imports NLTK, downloads punkt/stopwords if missing, sets the module-level references, returns `True`; on any exception sets `_nltk_available = False` and sets regex-based fallback alternatives, returns `False`
    - In `EnhancedNLPProcessor.__init__`, remove `self.stop_words = set(stopwords.words('english'))` — replace with `self._stop_words = None` (lazy)
    - Add `_get_stop_words(self)` method that calls `_load_nltk()` and returns the loaded stopwords set or a hardcoded fallback set
    - In `generate_summary`, `_extractive_summary`, `extract_keywords_tfidf`, and any other method using `sent_tokenize`/`word_tokenize`/`stopwords`: call `_load_nltk()` first and use `_sent_tokenize`/`_word_tokenize`/`_stopwords_set` (or regex fallback if NLTK unavailable)
    - Keep `sklearn` import at module level (it does not crash on missing NLTK data)
    - Keep the module-level `nlp_processor = EnhancedNLPProcessor()` instance
    - _Bug_Condition: isBugCondition_2(environment) where NLTK data absent AND nlp_processor imported at startup_
    - _Expected_Behavior: importing analyzer.nlp_processor never raises LookupError/OSError; NLTK init deferred to first NLP call_
    - _Preservation: All existing EnhancedNLPProcessor public methods (extract_title, extract_abstract, extract_keywords, generate_summary, detect_technologies, detect_methodology, extract_authors, extract_year, etc.) continue to work correctly when NLTK IS available_
    - _Requirements: 2.2_

  - [x] 4.2 Verify Bug 2 exploration test now passes
    - **Property 1: Expected Behavior** - `nlp_processor.py` Imports Without Crashing
    - **IMPORTANT**: Re-run the SAME test from task 1 for Bug 2 — do NOT write a new test
    - Run: in environment without NLTK data, assert `import analyzer.nlp_processor` does NOT raise
    - **EXPECTED OUTCOME**: Test PASSES (confirms Bug 2 is fixed)
    - _Requirements: 2.2_

  - [x] 4.3 Verify preservation tests still pass after Bug 2 fix
    - **Property 2: Preservation** - Non-Buggy Code Paths Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Confirm `EnhancedNLPProcessor` methods return correct results when NLTK IS available
    - Confirm `nlp_processor` global instance is still accessible
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 5. Fix Bug 3 — Login form uses `AuthenticationForm` but users registered with email as username

  - [x] 5.1 Add `EmailLoginForm` to `analyzer/forms.py`
    - Add `EmailLoginForm(forms.Form)` class with:
      - `email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}))`
      - `password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'}))`
    - Add `__init__(self, request=None, *args, **kwargs)` that stores `self.request = request` and `self.user_cache = None`
    - Add `clean(self)` method: get `email` and `password` from `cleaned_data`, call `authenticate(request=self.request, username=email, password=password)`, if `None` raise `forms.ValidationError("Invalid email or password.")`, else set `self.user_cache = user`
    - Add `get_user(self)` method: return `self.user_cache`
    - _Bug_Condition: isBugCondition_3(login_attempt) where form_class == AuthenticationForm AND user.username == user.email_
    - _Expected_Behavior: login form shows "Email" label; authenticate() routes through EmailOrUsernameModelBackend; registered users can log in_
    - _Preservation: CustomRegistrationForm and DocumentUploadForm are NOT modified_
    - _Requirements: 2.3_

  - [x] 5.2 Update `login_view` in `analyzer/views.py` to use `EmailLoginForm`
    - Import `EmailLoginForm` from `.forms` (add to existing import line)
    - Replace `AuthenticationForm` with `EmailLoginForm` in `login_view`: `form = EmailLoginForm(request, data=request.POST or None)`
    - Keep the rest of `login_view` logic identical: `if form.is_valid(): user = form.get_user(); login(request, user); return redirect('dashboard')`
    - Remove or comment out the `from django.contrib.auth.forms import AuthenticationForm` import if it is no longer used elsewhere in the file
    - _Requirements: 2.3_

  - [x] 5.3 Verify Bug 3 exploration test now passes
    - **Property 1: Expected Behavior** - Login Succeeds with Email and Password
    - **IMPORTANT**: Re-run the SAME test from task 1 for Bug 3 — do NOT write a new test
    - Run: register user with email, POST to `login_view` with that email and password, assert 302 redirect to dashboard
    - Also assert login form field label is "Email"
    - **EXPECTED OUTCOME**: Test PASSES (confirms Bug 3 is fixed)
    - _Requirements: 2.3_

  - [x] 5.4 Verify preservation tests still pass after Bug 3 fix
    - **Property 2: Preservation** - Non-Buggy Code Paths Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Confirm `register_view` still creates users and logs them in correctly
    - Confirm `logout_view` still works
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 6. Fix Bug 4 — Email config uses port 465 with `EMAIL_USE_TLS=True`

  - [x] 6.1 Implement the fix in `paper_analyzer/settings.py`
    - Change `EMAIL_USE_TLS` default from `'True'` to `'False'`: `EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').lower() == 'true'`
    - Add `EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True').lower() == 'true'`
    - Keep `EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))` unchanged
    - Keep all other email settings (`EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`) unchanged
    - _Bug_Condition: isBugCondition_4(smtp_config) where EMAIL_PORT==465 AND EMAIL_USE_TLS==True AND EMAIL_USE_SSL!=True_
    - _Expected_Behavior: EMAIL_USE_SSL=True, EMAIL_USE_TLS=False for port 465; SMTP connection uses implicit SSL; OTP emails delivered_
    - _Preservation: All other settings (DATABASE, STATIC, MEDIA, AUTHENTICATION_BACKENDS, etc.) are NOT modified_
    - _Requirements: 2.4_

  - [x] 6.2 Verify Bug 4 exploration test now passes
    - **Property 1: Expected Behavior** - OTP Email Config Correct for Port 465
    - **IMPORTANT**: Re-run the SAME test from task 1 for Bug 4 — do NOT write a new test
    - Run: assert `settings.EMAIL_USE_SSL == True` and `settings.EMAIL_USE_TLS == False` when `EMAIL_PORT == 465`
    - **EXPECTED OUTCOME**: Test PASSES (confirms Bug 4 is fixed)
    - _Requirements: 2.4_

  - [x] 6.3 Verify preservation tests still pass after Bug 4 fix
    - **Property 2: Preservation** - Non-Buggy Code Paths Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Confirm all other Django settings are unchanged
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 7. Fix Bug 5 — `analyze_document` calls non-existent `extract_links` and `extract_references` on `MLProcessor`

  - [x] 7.1 Add `extract_links` and `extract_references` methods to `MLProcessor` in `analyzer/ml_model.py`
    - Add `extract_links(self, text: str) -> List[str]`: use `re.findall(r'https?://[^\s\)\]>,"]+', text)` and return up to 50 results; return `[]` if no matches
    - Add `extract_references(self, text: str) -> List[str]`: find the References/Bibliography section using regex (look for heading `References`, `Bibliography`, `Works Cited`); split into individual entries by numbered pattern (`[1]`, `1.`, etc.) or newline-separated blocks; return up to 100 entries; return `[]` if no references section found
    - Both methods must return `list` (never raise)
    - Place both methods in the `MLProcessor` class after the existing `extract_authors` method
    - _Bug_Condition: isBugCondition_5(ml_processor) where hasattr(ml_processor, 'extract_links')==False AND hasattr(ml_processor, 'extract_references')==False_
    - _Expected_Behavior: extract_links returns List[str] of URLs; extract_references returns List[str] of reference entries; getattr fallback no longer needed_
    - _Preservation: All existing MLProcessor methods (extract_authors, extract_keywords, detect_methodology, extract_abstract, extract_conclusion, extract_title, extract_goal, extract_impact, detect_technologies, extract_publication_year) are NOT modified_
    - _Requirements: 2.5_

  - [x] 7.2 Verify Bug 5 exploration test now passes
    - **Property 1: Expected Behavior** - `extract_links` and `extract_references` Exist and Return Lists
    - **IMPORTANT**: Re-run the SAME test from task 1 for Bug 5 — do NOT write a new test
    - Run: assert `hasattr(ml_processor, 'extract_links')` and `hasattr(ml_processor, 'extract_references')` and both return `list`
    - **EXPECTED OUTCOME**: Test PASSES (confirms Bug 5 is fixed)
    - _Requirements: 2.5_

  - [x] 7.3 Verify preservation tests still pass after Bug 5 fix
    - **Property 2: Preservation** - Non-Buggy Code Paths Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Confirm all existing `MLProcessor` methods still return correct types and values
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 8. Fix Bug 6 — `ask_question` returns `{"answer": {"summary": "..."}}` instead of plain string

  - [x] 8.1 Implement the fix in `analyzer/views.py` `ask_question` view
    - After `answer = rag_pipeline(document.content, question)`, add:
      ```python
      if isinstance(answer, dict):
          answer = answer.get('summary', str(answer))
      ```
    - Update the `JsonResponse` to: `return JsonResponse({'success': True, 'question': question, 'answer': answer})`
    - Do NOT modify `rag_pipeline` itself — only fix the view's handling of its return value
    - _Bug_Condition: isBugCondition_6(rag_pipeline_result) where isinstance(result, dict) AND 'summary' in result AND view passes result directly as answer_
    - _Expected_Behavior: JsonResponse contains {"answer": "<plain string>"} not {"answer": {"summary": "..."}}_
    - _Preservation: rag_pipeline function is NOT modified; analyze_document view is NOT modified in this task_
    - _Requirements: 2.6_

  - [x] 8.2 Verify Bug 6 exploration test now passes
    - **Property 1: Expected Behavior** - `ask_question` Returns Plain String Answer
    - **IMPORTANT**: Re-run the SAME test from task 1 for Bug 6 — do NOT write a new test
    - Run: call `ask_question` view and assert `isinstance(response.json()['answer'], str)`
    - **EXPECTED OUTCOME**: Test PASSES (confirms Bug 6 is fixed)
    - _Requirements: 2.6_

  - [x] 8.3 Verify preservation tests still pass after Bug 6 fix
    - **Property 2: Preservation** - Non-Buggy Code Paths Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Confirm `rag_pipeline` still returns `{"summary": "..."}` (unchanged)
    - Confirm `analyze_document` view is unaffected
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 9. Checkpoint — Ensure all tests pass
  - Re-run the full test suite (all exploration tests from task 1 and all preservation tests from task 2)
  - All six Bug Condition exploration tests must PASS (bugs are fixed)
  - All Preservation tests must PASS (no regressions introduced)
  - Manually verify the end-to-end flows:
    - Upload a PDF → analysis completes with non-empty `summary`, `keywords`, `methodology` fields
    - Register with email → log out → log in with same email → redirected to dashboard
    - Request password reset → OTP email sent (or mock SMTP confirms correct SSL config)
    - Ask a question about a document → receive plain string answer in JSON response
    - Django server starts without error even when NLTK data is absent
  - Ensure all tests pass; ask the user if questions arise.
