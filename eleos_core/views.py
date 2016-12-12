from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Integration

# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You're at the eleos_core index.")


@login_required()
def listUserIntegrations(request):

    integrations = Integration.objects.all()

    return render(request, "integrations.html", {"integrations": integrations})
