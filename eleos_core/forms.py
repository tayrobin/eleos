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

class MomentForm():

    trigger = forms.CharField(label="Trigger", required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'trigger'}))

    # actually JSON, validated below
    content = forms.CharField(label="Content", required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'content'}))


    place_id = forms.IntegerField(label="Place ID", required=False,
                                widget=forms.NumberInput(attrs={'class': 'form-control', 'name': 'place_id'}))

    # latlng geography(Point,4326)
    latlng = None
    lat = forms.DecimalField(label="Latitude", required=False,
                                widget=forms.NumberInput(attrs={'class': 'form-control', 'name': 'lat'}))
    lng = forms.DecimalField(label="Longitude", required=False,
                                widget=forms.NumberInput(attrs={'class': 'form-control', 'name': 'lng'}))
    radius = forms.IntegerField(label="Radius in Meters", required=False,
                                widget=forms.NumberInput(attrs={'class': 'form-control', 'name': 'radius'}))

    # time_range time without time zone[]
    time_range = None

    # category_ids integer[]
    category_ids = None

    # venue_type_ids integer[]
    venue_type_ids = None

    def clean_jsonfield(self):
        import json
        jdata = self.cleaned_data['content']
        try:
            json_data = json.loads(jdata)
        except:
            raise forms.ValidationError("Invalid data in jsonfield")
        return jdata
