from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    INPUT_TYPE_CHOICES = [
        ('pdf', 'PDF File'),
        ('text', 'Raw Text'),
        ('url', 'URL'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    input_type = models.CharField(max_length=10, choices=INPUT_TYPE_CHOICES)
    title = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='uploads/', null=True, blank=True)
    url = models.URLField(max_length=2000, null=True, blank=True)
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
    
    def __str__(self):
        return self.title or f"{self.get_input_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_input_type_display_class(self):
        icons = {'pdf': 'fa-file-pdf', 'text': 'fa-file-alt', 'url': 'fa-globe'}
        return icons.get(self.input_type, 'fa-file')


class AnalysisResult(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='analysis')
    
    summary = models.TextField(blank=True)
    abstract = models.TextField(blank=True)
    keywords = models.JSONField(default=list)
    methodology = models.JSONField(default=list)
    technologies = models.JSONField(default=list)
    goal = models.TextField(blank=True)
    impact = models.TextField(blank=True)
    publication_year = models.CharField(max_length=10, blank=True)
    model_used = models.CharField(max_length=200, blank=True)  # AI/ML model used in research
    
    extracted_links = models.JSONField(default=list)
    dataset_names = models.JSONField(default=list)
    dataset_links = models.JSONField(default=list)
    references = models.JSONField(default=list)
    authors = models.JSONField(default=list)
    
    word_count = models.IntegerField(default=0)
    unique_words = models.IntegerField(default=0)
    character_count = models.IntegerField(default=0)

    # methodology_summary, plagiarism snapshot, PDF figure/image hints (JSON).
    extras = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Analysis Result'
        verbose_name_plural = 'Analysis Results'
    
    def __str__(self):
        return f"Analysis for: {self.document.title[:50]}"


class PlagiarismCheck(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='plagiarism_checks')
    similarity_score = models.FloatField(default=0.0)
    matched_sources = models.JSONField(default=list)
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Plagiarism Check'
        verbose_name_plural = 'Plagiarism Checks'
    
    def __str__(self):
        return f"Plagiarism Check for {self.document.title[:30]}"


class AnalysisFeedback(models.Model):
    RATING_CHOICES = [
        ('inaccurate', 'Inaccurate'),
        ('somewhat', 'Somewhat Accurate'),
        ('accurate', 'Accurate'),
        ('very-accurate', 'Very Accurate'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.CharField(max_length=20, choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Analysis Feedback'
        verbose_name_plural = 'Analysis Feedbacks'
    
    def __str__(self):
        return f"Feedback for {self.document.title[:30]} - {self.rating}"


class ComparisonResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comparisons')
    document1 = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='comparisons_as_first')
    document2 = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='comparisons_as_second', null=True, blank=True)
    input_text = models.TextField(blank=True, help_text="Text input for comparison (when not comparing two documents)")
    similarity_score = models.FloatField(default=0.0)
    comparison_data = models.JSONField(default=dict, help_text="Detailed comparison results")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comparison Result'
        verbose_name_plural = 'Comparison Results'
    
    def __str__(self):
        return f"Comparison {self.id} - {self.similarity_score}% similarity"


class PasswordResetOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Password Reset OTP'
        verbose_name_plural = 'Password Reset OTPs'
    
    def __str__(self):
        return f"OTP for {self.email}"
    
    def is_valid(self):
        """Check if OTP is still valid and not used"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at


class ContactMessage(models.Model):
    """Store contact form messages from visitors"""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=500)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
    
    def __str__(self):
        return f"{self.subject} - {self.name} ({self.email})"
