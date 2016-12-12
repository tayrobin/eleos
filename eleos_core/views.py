from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You're at the eleos_core index.")


@login_required(login_url="login/")
def listUserIntegrations(request):
    return render(request,"integrations.html")
