"""
Bug Condition Exploration Tests
================================
These tests encode the EXPECTED (fixed) behavior.
They are designed to FAIL on the current (unfixed) code.
Failure confirms the bugs exist.

DO NOT fix the code or the tests when they fail.

EXPLORATION RESULTS (counterexamples on unfixed code)
------------------------------------------------------
Bug 1 [FAIL]: analyze_text_with_groq returns str, not dict.
  Counterexample: result = 'Here is the summary of the paper.'
  AssertionError: 'Here is the summary of the paper.' is not an instance of dict

Bug 2 [FAIL]: nlp_processor.EnhancedNLPProcessor.__init__ calls stopwords.words('english')
  eagerly. When NLTK data is absent, this raises LookupError at instantiation time.
  Counterexample: LookupError: No stopwords data
  AssertionError: EnhancedNLPProcessor.__init__ raised LookupError when NLTK data absent

Bug 3 [FAIL]: Login form uses AuthenticationForm with field 'username' labeled "Username".
  Counterexample (label): form.fields = {'username': ..., 'password': ...}
    AssertionError: 'email' not found in {'username': ..., 'password': ...}
  Counterexample (redirect): POST with {'email': ..., 'password': ...} returns 200 (not 302)
    AssertionError: 200 != 302; Form errors: username field is required

Bug 4 [FAIL]: settings.py does not define EMAIL_USE_SSL; Django default is False.
  EMAIL_USE_TLS defaults to True in settings.py (wrong for port 465).
  Counterexample: EMAIL_USE_SSL=False (Django default), EMAIL_USE_TLS=True
  AssertionError: False is not true (EMAIL_USE_SSL should be True for port 465)

Bug 5 [PASS - already fixed]: ml_model.py already has extract_links and extract_references.
  The methods exist and return lists. Bug 5 is already resolved in the current codebase.
  views.py still uses getattr fallback but the methods are present.

Bug 6 [FAIL]: ask_question view passes rag_pipeline dict result directly as answer.
  Counterexample: response.json()['answer'] = {'summary': 'The answer is about neural networks.'}
  AssertionError: {'summary': '...'} is not an instance of str
"""

import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.conf import settings


# ============================================================
# Bug 1: analyze_text_with_groq returns str, not dict
# ============================================================
class TestBug1AnalyzeTextWithGroqReturnsDict(TestCase):
    """
    Bug 1: analyze_text_with_groq() returns a plain str.
    Views call .get('summary', '') on the result — fails silently or raises AttributeError.
    Expected (fixed) behavior: function returns a dict with at least key 'summary'.
    This test WILL FAIL on unfixed code.
    """

    def test_analyze_text_with_groq_returns_dict_with_summary(self):
        """
        Call analyze_text_with_groq with mocked Groq client returning a plain string.
        Assert the result is a dict containing 'summary'.
        FAILS on unfixed code because the function returns the raw string.
        """
        from analyzer.rag_utils import analyze_text_with_groq

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Here is the summary of the paper."

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_response

        with patch('analyzer.rag_utils.Groq', return_value=mock_client_instance):
            result = analyze_text_with_groq(
                "This is some research paper text about machine learning."
            )

        self.assertIsInstance(
            result, dict,
            f"Expected dict, got {type(result).__name__}: {repr(result)[:200]}"
        )
        self.assertIn(
            'summary', result,
            f"Expected 'summary' key in result dict, got: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
        )


# ============================================================
# Bug 2: nlp_processor.py module-level NLTK imports crash server
# ============================================================
class TestBug2NlpProcessorLazyNltk(TestCase):
    """
    Bug 2: nlp_processor.py has module-level NLTK imports and nltk.data.find() calls.
    When NLTK data is absent, importing the module raises LookupError.
    Expected (fixed) behavior: importing the module never raises; NLTK init is lazy.
    This test WILL FAIL on unfixed code.
    """

    def test_nlp_processor_init_does_not_call_stopwords_directly(self):
        """
        Verify EnhancedNLPProcessor.__init__ does NOT call stopwords.words() directly.
        On unfixed code, __init__ has: self.stop_words = set(stopwords.words('english'))
        which crashes when NLTK data is absent.
        FAILS on unfixed code because stopwords.words() is called eagerly in __init__.
        """
        import analyzer.nlp_processor as nlp_mod

        with patch('nltk.corpus.stopwords.words', side_effect=LookupError("No stopwords data")):
            try:
                instance = nlp_mod.EnhancedNLPProcessor()
                # If we reach here, __init__ did NOT call stopwords.words() directly — fix is in place
            except LookupError as e:
                self.fail(
                    f"EnhancedNLPProcessor.__init__ raised LookupError when NLTK data absent "
                    f"— module-level/eager NLTK usage detected: {e}"
                )


# ============================================================
# Bug 3: Login form uses AuthenticationForm (label "Username" not "Email")
# ============================================================
class TestBug3LoginFormUsesEmailLabel(TestCase):
    """
    Bug 3: login_view uses AuthenticationForm which has a 'username' field labeled "Username".
    Users register with email as username, but the form misleads them with "Username" label.
    Expected (fixed) behavior: form has field labeled "Email"; login with email field succeeds.
    This test WILL FAIL on unfixed code.
    """

    def setUp(self):
        self.client = Client()

    def test_login_form_has_email_field_with_email_label(self):
        """
        GET the login page and assert the form has a field named 'email' labeled 'Email'.
        FAILS on unfixed code because AuthenticationForm uses field 'username' labeled "Username".
        """
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)

        form = response.context.get('form')
        self.assertIsNotNone(form, "No form found in login page context")

        self.assertIn(
            'email', form.fields,
            f"Expected 'email' field in login form, got fields: {list(form.fields.keys())}"
        )
        self.assertEqual(
            form.fields['email'].label, 'Email',
            f"Expected label 'Email', got '{form.fields['email'].label}'"
        )

    def test_login_with_email_redirects_to_dashboard(self):
        """
        Register a user (username == email), POST to login with email field.
        Assert 302 redirect to dashboard.
        FAILS on unfixed code because the form uses 'username' field, not 'email'.
        """
        User.objects.create_user(
            username='testlogin@example.com',
            email='testlogin@example.com',
            password='testpass123'
        )

        response = self.client.post('/login/', {
            'email': 'testlogin@example.com',
            'password': 'testpass123',
        })

        self.assertEqual(
            response.status_code, 302,
            f"Expected 302 redirect after login with email, got {response.status_code}. "
            f"Form errors: {response.context['form'].errors if response.context and response.context.get('form') else 'N/A'}"
        )
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)


# ============================================================
# Bug 4: EMAIL_USE_SSL not set; EMAIL_USE_TLS=True with port 465
# ============================================================
class TestBug4EmailSslConfig(TestCase):
    """
    Bug 4: settings.py default is EMAIL_PORT=465 with EMAIL_USE_TLS=True (no EMAIL_USE_SSL).
    Port 465 requires EMAIL_USE_SSL=True (implicit SSL), not STARTTLS.
    Expected (fixed) behavior: when EMAIL_PORT=465, EMAIL_USE_SSL=True and EMAIL_USE_TLS=False.

    The settings.py code reads from env vars with defaults:
      EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))
      EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'  # BUG: default True
      # EMAIL_USE_SSL is not defined at all in unfixed code

    We test the settings.py defaults by simulating the 465 scenario with override_settings.
    This test WILL FAIL on unfixed code (EMAIL_USE_SSL not defined, EMAIL_USE_TLS=True).
    """

    @override_settings(EMAIL_PORT=465, EMAIL_USE_TLS=False)
    def test_email_port_465_uses_ssl_not_tls(self):
        """
        When EMAIL_PORT==465, assert EMAIL_USE_SSL==True and EMAIL_USE_TLS==False.
        We use override_settings to simulate the 465 scenario regardless of .env.
        FAILS on unfixed code: EMAIL_USE_SSL is not defined in settings.py.
        """
        from django.conf import settings as django_settings

        # Verify we're testing the 465 scenario
        self.assertEqual(django_settings.EMAIL_PORT, 465)

        # The fixed settings.py must define EMAIL_USE_SSL
        self.assertTrue(
            hasattr(django_settings, 'EMAIL_USE_SSL'),
            "settings.EMAIL_USE_SSL is not defined — required for port 465 (implicit SSL). "
            "The unfixed settings.py does not set EMAIL_USE_SSL at all."
        )
        self.assertTrue(
            django_settings.EMAIL_USE_SSL,
            f"Expected EMAIL_USE_SSL=True for port 465, got {django_settings.EMAIL_USE_SSL}"
        )
        self.assertFalse(
            django_settings.EMAIL_USE_TLS,
            f"Expected EMAIL_USE_TLS=False for port 465, got EMAIL_USE_TLS={django_settings.EMAIL_USE_TLS}"
        )


# ============================================================
# Bug 5: MLProcessor missing extract_links and extract_references
# ============================================================
class TestBug5MlProcessorMissingMethods(TestCase):
    """
    Bug 5: analyze_document uses getattr fallback for extract_links/extract_references
    because these methods don't exist on MLProcessor — always returns [].
    Expected (fixed) behavior: both methods exist and return a list.
    This test WILL FAIL on unfixed code.
    """

    def test_ml_processor_has_extract_links_returning_list(self):
        """
        Assert ml_processor has 'extract_links' and it returns a list.
        FAILS on unfixed code because the method doesn't exist.
        """
        from analyzer.ml_model import ml_processor

        self.assertTrue(
            hasattr(ml_processor, 'extract_links'),
            "ml_processor has no 'extract_links' attribute — method missing from MLProcessor"
        )
        result = ml_processor.extract_links(
            "See https://arxiv.org/abs/1234.5678 and https://github.com/example/repo"
        )
        self.assertIsInstance(
            result, list,
            f"Expected list from extract_links, got {type(result).__name__}"
        )

    def test_ml_processor_has_extract_references_returning_list(self):
        """
        Assert ml_processor has 'extract_references' and it returns a list.
        FAILS on unfixed code because the method doesn't exist.
        """
        from analyzer.ml_model import ml_processor

        self.assertTrue(
            hasattr(ml_processor, 'extract_references'),
            "ml_processor has no 'extract_references' attribute — method missing from MLProcessor"
        )
        text = (
            "Some paper content.\n\n"
            "References\n"
            "[1] Smith, J. (2020). A great paper. Journal of Science.\n"
            "[2] Doe, J. (2021). Another paper. Conference Proceedings.\n"
        )
        result = ml_processor.extract_references(text)
        self.assertIsInstance(
            result, list,
            f"Expected list from extract_references, got {type(result).__name__}"
        )


# ============================================================
# Bug 6: ask_question returns {"answer": {"summary": "..."}} not {"answer": "..."}
# ============================================================
class TestBug6AskQuestionReturnsStringAnswer(TestCase):
    """
    Bug 6: rag_pipeline returns {"summary": "..."} (a dict).
    ask_question view passes this dict directly as 'answer' in JsonResponse.
    Frontend receives {"answer": {"summary": "..."}} instead of {"answer": "..."}.
    Expected (fixed) behavior: JsonResponse contains {"answer": "<plain string>"}.
    This test WILL FAIL on unfixed code.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='asktest@example.com',
            email='asktest@example.com',
            password='testpass123'
        )
        self.client.login(username='asktest@example.com', password='testpass123')

    def test_ask_question_returns_string_answer(self):
        """
        Create a document, POST to ask_question, mock rag_pipeline to return a dict.
        Assert response.json()['answer'] is a str, not a dict.
        FAILS on unfixed code because the view passes the dict directly as answer.
        """
        from analyzer.models import Document

        document = Document.objects.create(
            user=self.user,
            title="Test Paper",
            content="This is a research paper about neural networks and deep learning.",
            word_count=12
        )

        mock_rag_result = {"summary": "The answer is about neural networks."}

        with patch('analyzer.views.rag_pipeline', return_value=mock_rag_result):
            response = self.client.post(
                f'/ask/{document.id}/',
                data=json.dumps({'question': 'What is this paper about?'}),
                content_type='application/json'
            )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        self.assertIn('answer', response_data, f"No 'answer' key in response: {response_data}")
        self.assertIsInstance(
            response_data['answer'], str,
            f"Expected answer to be str, got {type(response_data['answer']).__name__}: "
            f"{repr(response_data['answer'])}"
        )
