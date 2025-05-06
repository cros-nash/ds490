"""classes that generate HTML form elements and handle user input"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Project, APIKey, FieldSpecification

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class APIKeyForm(forms.ModelForm # creates form based on a model
                 ):
    class Meta:                  # configs form's behavior/appearance
        model = APIKey
        fields = ['key', 'provider']
        widgets = {              # configs how fields are rendered in html
            'key': forms.PasswordInput(render_value=True),
        }

class ProjectForm(forms.ModelForm # creates form based on a model
                  ):
    class Meta:
        model = Project
        fields = ['name', 'website', 'llm_input', 'respect_robots', 'pagination', 
                  'delay', 'max_pages', 'timeout', 'user_agent', 'verbose_logging',
                  'download_html', 'screenshot', 'output_format']
        widgets = {
            'llm_input': forms.Textarea(attrs={'rows': 5}),
        }

class FieldSpecificationForm(forms.ModelForm):
    class Meta:
        model = FieldSpecification
        fields = ['field_name', 'field_type', 'description']
        widgets = {
            'field_name': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief description of the field'}),
        }