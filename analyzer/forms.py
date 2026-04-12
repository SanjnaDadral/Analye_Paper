from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class DocumentUploadForm(forms.Form):
    INPUT_TYPE_CHOICES = [
        ('pdf', 'PDF File'),
        ('text', 'Raw Text'),
        ('url', 'URL'),
    ]
    
    input_type = forms.ChoiceField(choices=INPUT_TYPE_CHOICES, widget=forms.RadioSelect(attrs={
        'class': 'btn-check'
    }))
    
    pdf_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf',
            'id': 'pdfFile'
        })
    )
    
    text_content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Paste your research paper text here...',
            'id': 'textContent'
        })
    )
    
    url_input = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://example.com/research-paper',
            'id': 'urlInput'
        })
    )


class EmailForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter recipient email address'
        })
    )


class CustomRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        required=True,
        label="Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    class Meta:
        model = User
        fields = ('first_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Simple password hint - no strict requirements
        self.fields['password1'].help_text = "At least 8 characters"
        self.fields['password2'].help_text = "Confirm your password"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email.lower()
