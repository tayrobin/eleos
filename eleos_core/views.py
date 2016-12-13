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
    """
    {u'checkin': [u'{"id":"584fb810dad26340511f798c","createdAt":1481619472,"type":"checkin",
    "timeZone":"America\\/Los_Angeles","timeZoneOffset":-480,"user":{"id":"147283036",
    "firstName":"Taylor","lastName":"Robinson","gender":"male","relationship":"self",
    "photo":"https:\\/\\/irs3.4sqi.net\\/img\\/user\\/110\\/147283036-QD54DS4RIHBQWNU2.jpg"},
    "venue":{"id":"4f6c317de4b08a0bb8f4e65a","name":"Silicon Valley","contact":{},
    "location":{"lat":37.37433343892376,"lng":-121.9569512394378,"labeledLatLngs":[{"label":"display",
    "lat":37.37433343892376,"lng":-121.9569512394378}],"postalCode":"95051","cc":"US",
    "city":"Santa Clara","state":"CA","country":"United States","formattedAddress":["Santa Clara, CA 95051"]},
    "categories":[{"id":"4bf58dd8d48988d162941735","name":"Other Great Outdoors",
    "pluralName":"Other Great Outdoors","shortName":"Other Outdoors",
    "icon":"https:\\/\\/ss3.4sqi.net\\/img\\/categories\\/parks_outdoors\\/default.png",
    "parents":["Outdoors & Recreation"],"primary":true}],"verified":false,"stats":{"checkinsCount":3114,
    "usersCount":1224,"tipCount":4},"venueRatingBlacklisted":true,"beenHere":{"lastCheckinExpiredAt":0}}}'],
    u'secret': [u'0BJPRG1FEG02NBS10SFLZDLW14LGHHZHFNILLM2TEGUXIVD0'], u'user': [u'{"id":"147283036",
    "firstName":"Taylor","lastName":"Robinson","gender":"male","relationship":"self",
    "photo":"https:\\/\\/irs3.4sqi.net\\/img\\/user\\/110\\/147283036-QD54DS4RIHBQWNU2.jpg",
    "tips":{"count":0},"lists":{"groups":[{"type":"created","count":2,"items":[]}]},
    "homeCity":"California","bio":"","contact":{"phone":"3178094648","verifiedPhone":"true",
    "email":"taylor.howard.robinson@gmail.com","twitter":"_t_rob"}}']}
    """
    return HttpResponse(status=201)


def foursquareDetails(user, access_token):

    # get user profile
    response = requests.get('https://api.foursquare.com/v2/users/self', {'oauth_token':access_token, 'v':'20161212'})
    data = response.json()
    print user.username, "User Profile", data

    # get checkin history
    response = requests.get('https://api.foursquare.com/v2/users/self/checkins', {'oauth_token':access_token, 'v':'20161212'})
    data = response.json()
    print user.username, "Checkin History", data


def sendOAuth(request, integrationName):

    integration = get_object_or_404(Integration, name=integrationName)

    if not integration.auth_url:
        return redirect('/')
    else:
        if integration.name == 'Swarm':
            return redirect(integration.auth_url+"?"+"client_id="+os.environ['FOURSQUARE_CLIENT_ID']+
                                                    "&"+"response_type="+"code"+
                                                    "&"+"redirect_uri="+"https://eleos-core.herokuapp.com/receiveOAuth")
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
    print request.user.username, "Swarm", access_token

    # pull history
    foursquareDetails(request.user, access_token)

    # send back to integrations
    return redirect('/integrations')
