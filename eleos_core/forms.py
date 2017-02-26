from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

# If you don't do this you cannot use Bootstrap CSS
class LoginForm(AuthenticationForm):

    username = forms.CharField(label="Username", required=True,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'username'}))
    password = forms.CharField(label="Password", required=True,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'name': 'password'}))


class SignupForm(UserCreationForm):

    username = forms.CharField(label="Username", required=True,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'username'}))
    password1 = forms.CharField(label="Password1", required=True,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'name': 'password1'}))
    password2 = forms.CharField(label="Password2", required=True,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'name': 'password2'}))
