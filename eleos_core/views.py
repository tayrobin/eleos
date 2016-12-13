import os
import requests
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
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


@csrf_exempt
def foursquareCheckin(request):

    data = request.POST
    print data
    return HttpResponse(status=201)


def sendOAuth(request, integrationName):

    integration = get_object_or_404(Integration, name=integrationName)

    if not integration.auth_url:
        return redirect('/')
    else:
        if integration.name == 'Swarm':
            return redirect(integration.auth_url, {"client_id":os.environ['FOURSQUARE_CLIENT_ID'],
                                                    "response_type":"code",
                                                    "redirect_uri":"https://eleos-core.herokuapp.com/receiveOAuth"})
        else:
            return redirect(integration.auth_url) # ++ params


def receiveOAuth(request):

    # parse CODE
    tempCode = request.GET['code']

    # send to CODE<-->Auth_Token URL
    if True:
        integration = get_object_or_404(Integration, name='Swarm')

        response = requests.get(integration.token_url, {"client_id":os.environ['FOURSQUARE_CLIENT_ID'],
                                                        "client_secret":os.environ['FOURSQUARE_CLIENT_SECRET'],
                                                        "grant_type":"authorization_code", "code":tempCode,
                                                        "redirect_uri":"https://eleos-core.herokuapp.com/receiveOAuth"})

        response = response.json()
        access_token = response['access_token']

    # Create new Link
    integration.users.add(request.user)

    # Store access_token in DB

    # send back to integrations
    return redirect('/integrations')
