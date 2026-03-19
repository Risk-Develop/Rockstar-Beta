from django import forms
from django.core.validators import validate_email, MinLengthValidator
from django.core.exceptions import ValidationError
import re


class SignupForm(forms.Form):
    employee_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-orange-400 bg-white',
            'placeholder': 'EMP-XXXX-XXXX',
            'aria-describedby': 'employee_number_help',
            'autocomplete': 'employee-number'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-orange-400 bg-white',
            'placeholder': 'example@email.com',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2.5 pr-10 border rounded focus:ring-2 focus:ring-orange-400 bg-white',
            'placeholder': 'Enter password',
            'autocomplete': 'new-password',
            'aria-describedby': 'password_help'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2.5 pr-10 border rounded focus:ring-2 focus:ring-orange-400 bg-white',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })
    )

    def clean_employee_number(self):
        employee_number = self.cleaned_data.get('employee_number', '').strip()
        if not employee_number:
            raise ValidationError("Employee number is required.")
        return employee_number

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("Email address is required.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        
        if not password:
            raise ValidationError("Password is required.")
        
        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter.")
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number.")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            errors.append("Password must contain at least one special character (!@#$%^&*...).")
        
        if errors:
            raise ValidationError(errors)
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise ValidationError({"confirm_password": "Passwords do not match."})

        return cleaned_data


class LoginForm(forms.Form):
    employee_number = forms.CharField(max_length=20)
    password = forms.CharField(widget=forms.PasswordInput)

