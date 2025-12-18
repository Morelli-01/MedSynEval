from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import EmailValidator
from .models import Clinician, Evaluation

class ClinicianRegistrationForm(UserCreationForm):
    # Explicitly define email field as required with proper widget
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'your.email@example.com',
            'class': 'form-control',
        }),
        error_messages={
            'required': 'Email address is required.',
            'invalid': 'Please enter a valid email address.',
        }
    )
    
    class Meta:
        model = Clinician
        fields = ('username', 'email', 'first_name', 'last_name', 'title', 'workplace', 'years_experience')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['title'].required = True
        self.fields['workplace'].required = True
        self.fields['years_experience'].required = True
        
        # Remove password help text
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['password2'].label = 'Confirm Password'
        
        # Add placeholders
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['first_name'].widget.attrs.update({'placeholder': 'First name'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Last name'})
        self.fields['title'].widget.attrs.update({'placeholder': 'e.g., MD, Radiologist, Cardiologist'})
        self.fields['workplace'].widget.attrs.update({'placeholder': 'Hospital or institution name'})
        self.fields['years_experience'].widget.attrs.update({'placeholder': 'Years of experience', 'min': '0'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})
    
    def clean_email(self):
        """Validate email and check for uniqueness"""
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Email address is required.')
        
        # Check if email already exists
        if Clinician.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        
        return email

class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ('is_real', 'confidence')
        widgets = {
            'is_real': forms.RadioSelect(choices=[(True, 'Real'), (False, 'Synthetic')]),
            'confidence': forms.RadioSelect(),
        }

class ClinicianProfileForm(forms.ModelForm):
    class Meta:
        model = Clinician
        fields = ('first_name', 'last_name', 'email', 'title', 'workplace', 'years_experience')
