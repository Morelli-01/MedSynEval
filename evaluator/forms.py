from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Clinician, Evaluation

class ClinicianRegistrationForm(UserCreationForm):
    class Meta:
        model = Clinician
        fields = ('username', 'email', 'first_name', 'last_name', 'title', 'years_experience')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email optional
        self.fields['email'].required = False
        # Remove password help text
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['password2'].label = 'Confirm Password'
        # Add placeholders
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['email'].widget.attrs.update({'placeholder': 'your.email@example.com (optional)'})
        self.fields['first_name'].widget.attrs.update({'placeholder': 'First name'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Last name'})
        self.fields['title'].widget.attrs.update({'placeholder': 'e.g., Dr., Prof.'})
        self.fields['years_experience'].widget.attrs.update({'placeholder': 'Years of experience'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})

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
        fields = ('first_name', 'last_name', 'email', 'title', 'years_experience')
