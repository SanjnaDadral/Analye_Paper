"""
Preservation Tests (Task 2)
============================
These tests verify that non-buggy code paths work correctly on the CURRENT (unfixed) code.
They establish the baseline behavior that must be preserved after each fix.

ALL tests in this file MUST PASS on unfixed code.
They will be re-run after each fix to confirm no regressions.

Requirements covered: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 3.8
"""

import io
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth.models import User

from analyzer.models import Document, AnalysisResult, ContactMessage


# ============================================================
# Preservation 1 (Req 3.1): Dashboard returns 200 for authenticated user
# ============================================================
class TestPreservation1Dashboard(TestCase):
    """
    Authenticated GET to /dashboard/ must return 200.
    This verifies the dashboard view is unaffected by any fixes.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='dashuser@example.com',
            email='dashuser@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

    def test_authenticated_get_dashboard_returns_200(self):
        """Authenticated GET /dashboard/ returns HTTP 200."""
        response = self.client.get('/dashboard/')
        self.assertEqual(
            response.status_code, 200,
            f"Expected 200 from /dashboard/, got {response.status_code}"
        )

    def test_unauthenticated_dashboard_redirects(self):
        """Unauthenticated GET /dashboard/ redirects (not 200 or 500)."""
        anon_client = Client()
        response = anon_client.get('/dashboard/')
        self.assertIn(
            response.status_code, [301, 302],
            f"Expected redirect for unauthenticated dashboard, got {response.status_code}"
        )


# ============================================================
# Preservation 2 (Req 3.2): PDF text extraction via pdf_processor works
# ============================================================
class TestPreservation2PdfExtraction(TestCase):
    """
    pdf_processor.extract_text must return {'success': True, 'text': <non-empty str>}
    when given a valid PDF file. We mock the underlying PDF library to avoid needing
    a real PDF file.
    """

    def test_pdf_processor_extract_text_returns_success_with_text(self):
        """
        Mock pypdf to return text. Assert extract_text returns success=True and non-empty text.
        PdfReader is imported inside _extract_with_pypdf, so we patch 'pypdf.PdfReader'.
        """
        from analyzer.pdf_processor import get_pdf_processor

        processor = get_pdf_processor()

        # Build a minimal mock for pypdf PdfReader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is extracted text from the research paper."

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader.metadata = None

        mock_pdf_file = io.BytesIO(b"%PDF-1.4 fake content")
        mock_pdf_file.name = "test.pdf"

        with patch('pypdf.PdfReader', return_value=mock_reader):
            result = processor._extract_with_pypdf(mock_pdf_file)

        self.assertTrue(
            result.get('success'),
            f"Expected success=True, got: {result}"
        )
        self.assertIsInstance(
            result.get('text'), str,
            f"Expected text to be str, got {type(result.get('text'))}"
        )
        self.assertGreater(
            len(result.get('text', '')), 0,
            "Expected non-empty text from PDF extraction"
        )

    def test_pdf_processor_extract_text_structure(self):
        """
        The result dict from extract_text must have 'success' and 'text' keys.
        """
        from analyzer.pdf_processor import get_pdf_processor

        processor = get_pdf_processor()

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Machine learning paper content here."

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader.metadata = None

        mock_pdf_file = io.BytesIO(b"%PDF-1.4 fake")
        mock_pdf_file.name = "test.pdf"

        with patch('pypdf.PdfReader', return_value=mock_reader):
            result = processor._extract_with_pypdf(mock_pdf_file)

        self.assertIn('success', result, "Result must have 'success' key")
        self.assertIn('text', result, "Result must have 'text' key")


# ============================================================
# Preservation 3 (Req 3.3): Contact form saves ContactMessage and returns JSON success
# ============================================================
class TestPreservation3ContactForm(TestCase):
    """
    POST to /contact/ with valid data must save a ContactMessage and return JSON success.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='contactuser@example.com',
            email='contactuser@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

    def test_contact_post_saves_message_and_returns_success(self):
        """POST valid contact data → ContactMessage saved, JSON success=true."""
        initial_count = ContactMessage.objects.count()

        response = self.client.post('/contact/', {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Hello',
            'message': 'This is a test message from the preservation test.',
        })

        self.assertEqual(
            response.status_code, 200,
            f"Expected 200 from /contact/, got {response.status_code}"
        )

        data = response.json()
        self.assertTrue(
            data.get('success'),
            f"Expected success=true in response, got: {data}"
        )

        self.assertEqual(
            ContactMessage.objects.count(), initial_count + 1,
            "Expected ContactMessage count to increase by 1"
        )

    def test_contact_post_missing_required_fields_returns_failure(self):
        """POST with missing required fields returns success=false (not a crash)."""
        response = self.client.post('/contact/', {
            'name': '',
            'email': '',
            'subject': '',
            'message': '',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(
            data.get('success'),
            f"Expected success=false for missing fields, got: {data}"
        )


# ============================================================
# Preservation 4 (Req 3.4): MLProcessor existing methods return correct types
# ============================================================
class TestPreservation4MLProcessorMethods(TestCase):
    """
    Existing MLProcessor methods must return the correct types.
    These methods must be unaffected by any fixes.
    """

    def setUp(self):
        from analyzer.ml_model import ml_processor
        self.ml = ml_processor

    def test_extract_keywords_returns_list(self):
        """extract_keywords returns a list."""
        result = self.ml.extract_keywords("machine learning deep neural networks classification")
        self.assertIsInstance(
            result, list,
            f"extract_keywords should return list, got {type(result).__name__}"
        )

    def test_detect_methodology_returns_list(self):
        """detect_methodology returns a list."""
        result = self.ml.detect_methodology(
            "We used a quantitative approach with surveys and statistical analysis."
        )
        self.assertIsInstance(
            result, list,
            f"detect_methodology should return list, got {type(result).__name__}"
        )

    def test_extract_title_returns_str(self):
        """extract_title returns a str."""
        result = self.ml.extract_title(
            "Deep Learning for Natural Language Processing\nAbstract: This paper..."
        )
        self.assertIsInstance(
            result, str,
            f"extract_title should return str, got {type(result).__name__}"
        )

    def test_extract_abstract_returns_str(self):
        """extract_abstract returns a str."""
        result = self.ml.extract_abstract(
            "Abstract\nThis paper presents a novel approach to machine learning.\n\nIntroduction\nMore text."
        )
        self.assertIsInstance(
            result, str,
            f"extract_abstract should return str, got {type(result).__name__}"
        )

    def test_detect_technologies_returns_list(self):
        """detect_technologies returns a list."""
        result = self.ml.detect_technologies(
            "We implemented the model using Python and TensorFlow on AWS."
        )
        self.assertIsInstance(
            result, list,
            f"detect_technologies should return list, got {type(result).__name__}"
        )

    def test_extract_authors_returns_list(self):
        """extract_authors returns a list."""
        result = self.ml.extract_authors(
            "Authors: John Smith, Jane Doe\nAbstract: This paper..."
        )
        self.assertIsInstance(
            result, list,
            f"extract_authors should return list, got {type(result).__name__}"
        )

    def test_extract_conclusion_returns_str(self):
        """extract_conclusion returns a str."""
        result = self.ml.extract_conclusion(
            "Introduction\nSome text.\n\nConclusion\nIn this paper we showed that deep learning works."
        )
        self.assertIsInstance(
            result, str,
            f"extract_conclusion should return str, got {type(result).__name__}"
        )

    def test_extract_goal_returns_str(self):
        """extract_goal returns a str."""
        result = self.ml.extract_goal(
            "The goal of this paper is to improve accuracy of classification models."
        )
        self.assertIsInstance(
            result, str,
            f"extract_goal should return str, got {type(result).__name__}"
        )


# ============================================================
# Preservation 5 (Req 3.5): Export endpoint returns valid JSON
# ============================================================
class TestPreservation5ExportEndpoint(TestCase):
    """
    GET /export/<id>/json/ must return HTTP 200 with valid JSON content.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='exportuser@example.com',
            email='exportuser@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

        self.document = Document.objects.create(
            user=self.user,
            title="Test Export Paper",
            content="This is a research paper about machine learning.",
            input_type='text',
            word_count=9
        )

        self.analysis = AnalysisResult.objects.create(
            document=self.document,
            summary="A summary of the paper.",
            abstract="An abstract of the paper.",
            keywords=["machine learning", "deep learning"],
            methodology=["Experimental"],
            technologies=["Python"],
            goal="To improve accuracy.",
            impact="Significant improvement.",
            word_count=9,
        )

    def test_export_json_returns_200_and_valid_json(self):
        """GET /export/<id>/json/ returns 200 and valid JSON."""
        response = self.client.get(f'/export/{self.document.id}/json/')

        self.assertEqual(
            response.status_code, 200,
            f"Expected 200 from export endpoint, got {response.status_code}"
        )

        # Verify it's valid JSON
        try:
            data = response.json()
        except Exception as e:
            self.fail(f"Response is not valid JSON: {e}")

        self.assertIn('title', data, "JSON export must contain 'title' key")

    def test_export_json_without_analysis_returns_200(self):
        """Export works even when no AnalysisResult exists."""
        doc_no_analysis = Document.objects.create(
            user=self.user,
            title="No Analysis Paper",
            content="Some content.",
            input_type='text',
            word_count=2
        )

        response = self.client.get(f'/export/{doc_no_analysis.id}/json/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('title', data)


# ============================================================
# Preservation 6 (Req 3.7): Document deletion returns success JSON
# ============================================================
class TestPreservation6DocumentDeletion(TestCase):
    """
    POST to /delete/<id>/ must return HTTP 200 with success=true JSON,
    and the document must no longer exist.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='deleteuser@example.com',
            email='deleteuser@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

    def test_delete_document_returns_success_and_removes_document(self):
        """POST /delete/<id>/ returns success=true and document is gone."""
        document = Document.objects.create(
            user=self.user,
            title="Paper to Delete",
            content="Some content.",
            input_type='text',
            word_count=2
        )
        doc_id = document.id

        response = self.client.post(f'/delete/{doc_id}/')

        self.assertEqual(
            response.status_code, 200,
            f"Expected 200 from delete endpoint, got {response.status_code}"
        )

        data = response.json()
        self.assertTrue(
            data.get('success'),
            f"Expected success=true in delete response, got: {data}"
        )

        self.assertFalse(
            Document.objects.filter(id=doc_id).exists(),
            "Document should no longer exist after deletion"
        )

    def test_delete_another_users_document_is_rejected(self):
        """Cannot delete another user's document — returns non-200 error response."""
        other_user = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpass123'
        )
        other_doc = Document.objects.create(
            user=other_user,
            title="Other User's Paper",
            content="Content.",
            input_type='text',
            word_count=1
        )

        response = self.client.post(f'/delete/{other_doc.id}/')
        # The view catches Http404 in a broad except and returns 500 (current behavior)
        # The important thing is: the document is NOT deleted
        self.assertNotEqual(
            response.status_code, 200,
            "Should not return 200 when deleting another user's document"
        )
        self.assertTrue(
            Document.objects.filter(id=other_doc.id).exists(),
            "Other user's document should NOT be deleted"
        )


# ============================================================
# Preservation 7 (Req 3.8): Registration creates user and redirects to dashboard
# ============================================================
class TestPreservation7Registration(TestCase):
    """
    POST to /register/ with valid data must create a user and redirect to dashboard.
    """

    def setUp(self):
        self.client = Client()

    def test_registration_creates_user_and_redirects_to_dashboard(self):
        """POST /register/ with valid data creates user and redirects to /dashboard/."""
        response = self.client.post('/register/', {
            'first_name': 'New User',
            'email': 'newuser@example.com',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
        })

        # Should redirect to dashboard
        self.assertIn(
            response.status_code, [301, 302],
            f"Expected redirect after registration, got {response.status_code}. "
            f"Form errors: {response.context['form'].errors if response.context and response.context.get('form') else 'N/A'}"
        )

        # User should be created
        self.assertTrue(
            User.objects.filter(email='newuser@example.com').exists(),
            "User should be created after registration"
        )

        # Should redirect to dashboard
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)

    def test_registration_with_duplicate_email_fails(self):
        """Registration with an already-used email returns form errors (not a crash)."""
        User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='testpass123'
        )

        response = self.client.post('/register/', {
            'first_name': 'Duplicate',
            'email': 'existing@example.com',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
        })

        # Should re-render the form (200), not crash
        self.assertEqual(
            response.status_code, 200,
            f"Expected 200 (form re-render) for duplicate email, got {response.status_code}"
        )


# ============================================================
# Preservation 8 (Req 3.8 / MLProcessor): Property-style test for MLProcessor return types
# ============================================================
class TestPreservation8MLProcessorReturnTypes(TestCase):
    """
    Property-based style test: for a range of text inputs, MLProcessor methods
    always return the correct type. Tests extract_keywords, detect_methodology,
    extract_title, extract_abstract with various text strings.

    Validates: Requirements 3.4, 3.8
    """

    def setUp(self):
        from analyzer.ml_model import ml_processor
        self.ml = ml_processor

    # Various text inputs to test across
    TEXT_INPUTS = [
        "",
        "a",
        "Short text.",
        "Machine learning is a subset of artificial intelligence.",
        "We used a quantitative approach with surveys and statistical analysis of 500 participants.",
        "Deep Learning for Natural Language Processing\nAbstract: This paper presents...\nIntroduction\nText.",
        "Authors: John Smith, Jane Doe\nAbstract: This paper proposes a novel method.\nKeywords: NLP, ML",
        "References\n[1] Smith, J. (2020). A paper. Journal.\n[2] Doe, J. (2021). Another. Conference.",
        "A" * 1000,  # long repeated text
        "The goal of this study is to improve accuracy. We used Python and TensorFlow. " * 20,
    ]

    def test_extract_keywords_always_returns_list(self):
        """extract_keywords returns list for all text inputs."""
        for text in self.TEXT_INPUTS:
            with self.subTest(text=text[:50]):
                result = self.ml.extract_keywords(text)
                self.assertIsInstance(
                    result, list,
                    f"extract_keywords({text[:30]!r}...) returned {type(result).__name__}, expected list"
                )

    def test_detect_methodology_always_returns_list(self):
        """detect_methodology returns list for all text inputs."""
        for text in self.TEXT_INPUTS:
            with self.subTest(text=text[:50]):
                result = self.ml.detect_methodology(text)
                self.assertIsInstance(
                    result, list,
                    f"detect_methodology({text[:30]!r}...) returned {type(result).__name__}, expected list"
                )

    def test_extract_title_always_returns_str(self):
        """extract_title returns str for all text inputs."""
        for text in self.TEXT_INPUTS:
            with self.subTest(text=text[:50]):
                result = self.ml.extract_title(text)
                self.assertIsInstance(
                    result, str,
                    f"extract_title({text[:30]!r}...) returned {type(result).__name__}, expected str"
                )

    def test_extract_abstract_always_returns_str(self):
        """extract_abstract returns str for all text inputs."""
        for text in self.TEXT_INPUTS:
            with self.subTest(text=text[:50]):
                result = self.ml.extract_abstract(text)
                self.assertIsInstance(
                    result, str,
                    f"extract_abstract({text[:30]!r}...) returned {type(result).__name__}, expected str"
                )

    def test_detect_technologies_always_returns_list(self):
        """detect_technologies returns list for all text inputs."""
        for text in self.TEXT_INPUTS:
            with self.subTest(text=text[:50]):
                result = self.ml.detect_technologies(text)
                self.assertIsInstance(
                    result, list,
                    f"detect_technologies({text[:30]!r}...) returned {type(result).__name__}, expected list"
                )

    def test_extract_authors_always_returns_list(self):
        """extract_authors returns list for all text inputs."""
        for text in self.TEXT_INPUTS:
            with self.subTest(text=text[:50]):
                result = self.ml.extract_authors(text)
                self.assertIsInstance(
                    result, list,
                    f"extract_authors({text[:30]!r}...) returned {type(result).__name__}, expected list"
                )

    def test_no_method_raises_on_any_input(self):
        """No MLProcessor method raises an exception for any of the test inputs."""
        methods_and_types = [
            ('extract_keywords', list),
            ('detect_methodology', list),
            ('extract_title', str),
            ('extract_abstract', str),
            ('detect_technologies', list),
            ('extract_authors', list),
            ('extract_conclusion', str),
            ('extract_goal', str),
        ]

        for text in self.TEXT_INPUTS:
            for method_name, expected_type in methods_and_types:
                with self.subTest(method=method_name, text=text[:30]):
                    try:
                        result = getattr(self.ml, method_name)(text)
                        self.assertIsInstance(result, expected_type)
                    except Exception as e:
                        self.fail(
                            f"{method_name}({text[:30]!r}...) raised {type(e).__name__}: {e}"
                        )
