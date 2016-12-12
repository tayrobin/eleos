from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Integration, Module

# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You're at the eleos_core index.")


@login_required()
def listIntegrations(request):

    activeIntegrations = Integration.objects.filter(users=request.user)
    inactiveIntegrations = Integration.objects.exclude(users=request.user)

    return render(request, "integrations.html", {"activeIntegrations": activeIntegrations,
                                                 "inactiveIntegrations": inactiveIntegrations})


@login_required()
def listModules(request):

    modules = Module.objects.all()

    return render(request, "modules.html", {"modules": modules})
