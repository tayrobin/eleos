from django.contrib.auth.forms import AuthenticationForm
from django import forms

# If you don't do this you cannot use Bootstrap CSS
class LoginForm(AuthenticationForm):

    username = forms.CharField(label="Username", required=True,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'username'}))
    password = forms.CharField(label="Password", required=True,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'name': 'password'}))
