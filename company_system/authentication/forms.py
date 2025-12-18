from django import forms

class SignupForm(forms.Form):
    employee_number = forms.CharField(max_length=20)
    name = forms.CharField(max_length=255)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

class LoginForm(forms.Form):
    employee_number = forms.CharField(max_length=20)
    password = forms.CharField(widget=forms.PasswordInput)
