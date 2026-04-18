# Bug Exploration Test Results

Tests run: `python manage.py test analyzer.tests.test_bug_exploration --verbosity=2`

**Total: 8 tests, 6 FAIL, 2 PASS**

---

## Bug 1 — `analyze_text_with_groq` Returns String, Not Dict

**Status: FAIL (bug confirmed)**

**Test**: `test_analyze_text_with_groq_returns_dict_with_summary`

**Counterexample**:
```
AssertionError: 'Here is the summary of the paper.' is not an instance of <class 'dict'>
Expected dict, got str: 'Here is the summary of the paper.'
```

**Root cause**: `analyze_text_with_groq` in `rag_utils.py` returns `response.choices[0].message.content` directly — a plain string. The view calls `.get('summary', '')` on it, which fails silently or raises `AttributeError`.

---

## Bug 2 — `nlp_processor.py` Module-Level NLTK Imports Crash Server

**Status: FAIL (bug confirmed)**

**Test**: `test_nlp_processor_init_does_not_call_stopwords_directly`

**Counterexample**:
```
LookupError: No stopwords data
AssertionError: EnhancedNLPProcessor.__init__ raised LookupError when NLTK data absent
— module-level/eager NLTK usage detected: No stopwords data
```

**Root cause**: `EnhancedNLPProcessor.__init__` calls `set(stopwords.words('english'))` eagerly. When NLTK data is absent and `stopwords.words` is patched to raise `LookupError`, instantiation fails. The module also has top-level `from nltk.tokenize import sent_tokenize, word_tokenize` and `from nltk.corpus import stopwords` imports.

---

## Bug 3 — Login Form Uses `AuthenticationForm` (Label "Username" Not "Email")

**Status: FAIL (bug confirmed)**

**Tests**: `test_login_form_has_email_field_with_email_label`, `test_login_with_email_redirects_to_dashboard`

**Counterexample 1** (wrong field/label):
```
AssertionError: 'email' not found in {'username': <UsernameField>, 'password': <CharField>}
Expected 'email' field in login form, got fields: ['username', 'password']
```

**Counterexample 2** (login fails with email field):
```
AssertionError: 200 != 302
Expected 302 redirect after login with email, got 200.
Form errors: <ul class="errorlist"><li>username<ul class="errorlist">
  <li>This field is required.</li></ul></li></ul>
```

**Root cause**: `login_view` uses `AuthenticationForm` which has a `username` field labeled "Username". Users who registered with email as username cannot log in via the `email` field because the form expects `username`.

---

## Bug 4 — Email Config Uses Port 465 with `EMAIL_USE_TLS=True`

**Status: FAIL (bug confirmed)**

**Test**: `test_email_port_465_uses_ssl_not_tls`

**Counterexample**:
```
AssertionError: False is not true
Expected EMAIL_USE_SSL=True for port 465, got False
```

**Root cause**: `settings.py` does not define `EMAIL_USE_SSL` (Django defaults it to `False`). The default `EMAIL_USE_TLS='True'` is wrong for port 465 which requires implicit SSL (`EMAIL_USE_SSL=True`). STARTTLS (`EMAIL_USE_TLS=True`) is for port 587.

---

## Bug 5 — `MLProcessor` Missing `extract_links` and `extract_references`

**Status: PASS (bug already fixed in current codebase)**

**Tests**: `test_ml_processor_has_extract_links_returning_list`, `test_ml_processor_has_extract_references_returning_list`

**Finding**: Both `extract_links` and `extract_references` methods already exist in `ml_model.py` (lines 775 and 800). The bug described in the spec appears to have been resolved prior to this bugfix spec. The `views.py` still uses `getattr` fallback but the methods are present and functional.

---

## Bug 6 — `ask_question` Returns `{"answer": {"summary": "..."}}` Not `{"answer": "..."}`

**Status: FAIL (bug confirmed)**

**Test**: `test_ask_question_returns_string_answer`

**Counterexample**:
```
AssertionError: {'summary': 'The answer is about neural networks.'} is not an instance of <class 'str'>
Expected answer to be str, got dict: {'summary': 'The answer is about neural networks.'}
```

**Root cause**: `rag_pipeline` returns `{"summary": "..."}` (a dict). The `ask_question` view passes this dict directly as `answer` in `JsonResponse({'answer': answer})`. The frontend receives `{"answer": {"summary": "..."}}` instead of `{"answer": "..."}`.
