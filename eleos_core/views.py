import os
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


def showTest(request):

    #myDict = {'APP_ID': os.environ['FACEBOOK_APP_ID'], 'PAGE_ID': os.environ['FACEBOOK_PAGE_ID']}
    pass
    #return render(request, 'test_messenger.html', myDict)


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


@csrf_exempt
def foursquareCheckin(request):

    dataDict = dict(request.POST)
    print "dataDict", dataDict
    dataJson = json.loads(request.POST)
    print "dataJson", dataJson
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
    if dataDict['checkin'][0]['user']['id'] == "147283036":

        # send intro message
        i = Integration.objects.get(name='Facebook')
        try:
            ai = ActiveIntegration.objects.get(user=request.user, integration=i)
            if ai.external_user_id:
                sendMessenger(recipientId=ai.external_user_id, messageText="Nice check in at %s!"%dataDict['checkin'][0]['venue']['name'])
        except:
            return HttpResponse(status=201)

    return HttpResponse(status=201)


def foursquareDetails(activeIntegration):

    # get user profile
    response = requests.get('https://api.foursquare.com/v2/users/self', {'oauth_token':activeIntegration.access_token, 'v':'20161212'})
    data = response.json()
    print activeIntegration.user.username, "User Profile", data

    try:
        user_id = data['response']['user']['id']
        activeIntegration.external_user_id = user_id
        activeIntegration.save()
    except:
        print "Unable to parse User ID from response."

    # get checkin history
    response = requests.get('https://api.foursquare.com/v2/users/self/checkins', {'oauth_token':activeIntegration.access_token, 'v':'20161212'})
    data = response.json()
    print activeIntegration.user.username, "Checkin History", data


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
        else:
            return redirect(integration.auth_url) # ++ params


@login_required()
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
        print request.user.username, integration.name, access_token

    # Create new Link
    activeIntegration, new = ActiveIntegration.objects.get_or_create(user=request.user, integration=integration, access_token=access_token)

    # pull history
    if new and integration.name=='Swarm':
        foursquareDetails(activeIntegration)

    # send back to integrations
    return redirect('/integrations')


@login_required()
def receiveFacebookOAuth(request):

    if request.method == 'GET':
        print "GET", request.GET
    elif request.method == 'POST':
        print "POST", request.POST
        print "DATA", request.body

    # parse CODE
    tempCode = request.GET['code']

    # send to CODE<-->Auth_Token URL
    integration = get_object_or_404(Integration, name='Facebook')

    response = requests.get(integration.token_url, {"client_id":os.environ['FACEBOOK_APP_ID'],
                                                    "client_secret":os.environ['FACEBOOK_APP_SECRET'],
                                                    "code":tempCode,
                                                    "redirect_uri":"https://eleos-core.herokuapp.com/receive_facebook_oauth"})

    response = response.json()
    access_token = response['access_token']
    print request.user.username, integration.name, access_token

    # Create new Link
    activeIntegration, new = ActiveIntegration.objects.get_or_create(user=request.user, integration=integration)
    if not activeIntegration.access_token:
        activeIntegration.access_token = access_token
        activeIntegration.save()

    # send back to integrations
    return redirect('/integrations')
