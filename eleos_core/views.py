import os
import json
import requests
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Integration, Module, ActiveIntegration
from .messenger_views import sendMessenger


@login_required()
def listIntegrations(request):

    integrations = Integration.objects.all()

    return render(request, "integrations.html", {"integrations": integrations, 'APP_ID': os.environ['FACEBOOK_APP_ID'], 'PAGE_ID': os.environ['FACEBOOK_PAGE_ID']})


@login_required()
def listModules(request):

    modules = Module.objects.all()

    return render(request, "modules.html", {"modules": modules})


@login_required()
def deleteActiveIntegration(request, name):

    integration = get_object_or_404(Integration, name=name)
    activeIntegration = get_object_or_404(ActiveIntegration, integration=integration, user=request.user)
    activeIntegration.delete()

    return redirect('/integrations')


@login_required()
def activateModule(request, id):

    module = get_object_or_404(Module, id=id)

    if request.user in module.users.all():
        pass
    else:
        for integration in module.required_integrations.all():
            if request.user not in integration.users.all():
                return redirect('/integrations')

        module.users.add(request.user)

        # send intro message
        i = Integration.objects.get(name='Facebook')
        ai = ActiveIntegration.objects.get(user=request.user, integration=i)
        if ai.external_user_id:
            sendMessenger(recipientId=ai.external_user_id, messageText=module.intro_message)

    return redirect('/modules')


@login_required()
def deactivateModule(request, id):

    module = get_object_or_404(Module, id=id)

    if request.user not in module.users.all():
        pass
    else:
        module.users.remove(request.user)

    return redirect('/modules')


def sendOAuth(request, integrationName):

    integration = get_object_or_404(Integration, name=integrationName)

    if not integration.auth_url:
        return redirect('/')
    else:
        if integration.name == 'Swarm':
            return redirect(integration.auth_url+"?"+"client_id="+os.environ['FOURSQUARE_CLIENT_ID']+
                                                    "&"+"response_type="+"code"+
                                                    "&"+"redirect_uri="+"https://eleos-core.herokuapp.com/receiveOAuth")
        elif integration.name == 'Facebook':
            return redirect(integration.auth_url+"?"+"app_id="+os.environ['FACEBOOK_APP_ID']+
                                                    "&"+"redirect_uri="+"https://eleos-core.herokuapp.com/receive_facebook_oauth")
        elif integration.name == 'Calendar':
            return redirect(integration.auth_url+"?"+"scope="+"https://www.googleapis.com/auth/calendar.readonly"+
                                                    "&"+"client_id="+os.environ['CALENDAR_CLIENT_ID']+
                                                    "&"+"redirect_uri="+"https://eleos-core.herokuapp.com/receive_calendar_oauth"+
                                                    "&"+"response_type="+"code"+
                                                    "&"+"access_type="+"offline")
        else:
            return redirect(integration.auth_url) # ++ params
