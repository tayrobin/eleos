from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse

# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You're at the eleos_core index.")


@login_required()
def listUserIntegrations(request):
    userIntegrations = [
                        {"name":"Facebook", "active":False, "link":"https://www.facebook.com/v2.8/dialog/oauth?"},
                        {"name":"Swarm", "active":True, "link":"https://foursquare.com/oauth2/authenticate"},
                        {"name":"Google Maps", "active":False, "link":"https://accounts.google.com/o/oauth2/v2/auth"}
                        ]

    return render(request, "integrations.html", {"integrations": userIntegrations})
