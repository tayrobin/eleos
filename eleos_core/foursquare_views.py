import os
import json
import time
import random
import logging
import requests
from celery import shared_task
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Integration, Module, ActiveIntegration, GiftedMoment
from .messenger_views import sendMessenger, callSendAPI

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)


@shared_task
def geocodeCoordinates(lat, lng):

    return {'name':'HanaHaus', 'city':'Palo Alto', 'country':'US', 'lat':lat, 'lng':lng}


@shared_task
def giveGiftedMoment(user_id, id=None):

    user = get_object_or_404(User, id=user_id)

    facebook = Integration.objects.get(name='Facebook')

    # get FBM ActiveIntegration
    try:
        ai_facebook = ActiveIntegration.objects.get(
            user=user, integration=facebook)
        logging.info(
            "Now have ActiveIntegration for FBM for %s" % ai_facebook.user)
    except:
        logging.warning(
            "Looks like %s hasn't given permission for FBM." % user)
        return HttpResponse(status=201)

    if id:
        giftedMoment = get_object_or_404(GiftedMoment, pk=id)
    else:

        giftedMoments = GiftedMoment.objects.filter(
            recipient=user, fbm_message_id=None)

        # deliver Moment (or generic response)
        if giftedMoments:
            giftedMoment = random.choice(giftedMoments)
        else:
            try:
                sendMessenger.apply_async(kwargs={'recipientId': ai_facebook.external_user_id,
                                                  'messageText': "Nice checkin at %s!" % venueName})
            except:
                logging.warning("Error calling sendMessenger()")
                return HttpResponse(status=201)


    messageData = {
        "recipient": {
            "id": ai_facebook.external_user_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": '%(creator)s created a %(length)s minute Moment for you:' % {'creator': giftedMoment.creator, 'length': giftedMoment.payload.length},
                            "image_url": giftedMoment.payload.image_url,
                            "subtitle": giftedMoment.endorsement,
                            "default_action": {
                                "type": "web_url",
                                "url": "https://eleos-core.herokuapp.com/deliver_gifted_moment/" + str(giftedMoment.id) + "/",
                                "messenger_extensions": True,
                                "webview_height_ratio": "tall",
                                "fallback_url": "https://eleos-core.herokuapp.com"
                            },
                            "buttons": [
                                {
                                    "type": "postback",
                                    "title": "Not a good Moment",
                                    "payload": "bad_moment_" + str(giftedMoment.id)
                                }, {
                                    "type": "postback",
                                    "title": "Thank %(creator)s" % {'creator': giftedMoment.creator},
                                    "payload": "thank_%(creator)s" % {'creator': giftedMoment.creator}
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }

    messageId = callSendAPI(messageData)
    if messageId:
        if '.' and ':' in messageId:
            messageId = messageId.split('.')[1].split(':')[0]
        giftedMoment.fbm_message_id = messageId
        giftedMoment.fbm_sent_status = True
        giftedMoment.fbm_message_sent_at = timezone.now()
        giftedMoment.save()
    else:
        logging.warning(
            "No messageId returned, delivery must have failed.")


@shared_task
def parseFoursquareCheckin(checkin):

    facebook = Integration.objects.get(name='Facebook')
    swarm = Integration.objects.get(name='Swarm')

    swarmUserId = checkin['user']['id']

    # get Swarm ActiveIntegration
    try:
        ai_swarm = ActiveIntegration.objects.get(
            external_user_id=swarmUserId, integration=swarm)
    except:
        logging.warning("Unable to find ActiveIntegration for this User.")
        return

    venueName = checkin['venue']['name']
    logging.info("@%s went to %s" % (ai_swarm.user, venueName))

    venueType = ''
    for cat in checkin['venue']['categories']:
        if 'primary' in cat and cat['primary']:
            if 'parents' in cat and cat['parents'] != []:
                venueType = cat['parents'][0]
            else:
                venueType = cat['name']
    logging.info("venueType: %s" % venueType)

    giftedMomentsList = GiftedMoment.objects.filter(recipient=ai_swarm.user, fbm_message_id=None, trigger='Swarm')

    delivered = False # only deliver 1 GiftedMoment per checkin

    for giftedMoment in giftedMomentsList:

        if not delivered:
            if giftedMoment.venue_type:
                venue_type = giftedMoment.get_venue_type_display()
                if venue_type == venueType:
                    # asynchronously check for and deliver a Moment
                    giveGiftedMoment.apply_async(args=[ai_swarm.user.id, giftedMoment.id], countdown=giftedMoment.delay)
                    delivered = True
            else:
                # asynchronously check for and deliver a Moment
                giveGiftedMoment.apply_async(args=[ai_swarm.user.id, giftedMoment.id], countdown=giftedMoment.delay)
                delivered = True


@csrf_exempt
def foursquareCheckin(request):

    logging.info(request.POST)
    dataJson = json.loads(dict(request.POST)['checkin'][0])
    logging.info("dataJson: %s" % dataJson)

    # handoff to async task
    parseFoursquareCheckin.apply_async(args=[dataJson])

    return HttpResponse(status=201)


@shared_task
def foursquareCheckinHistory(activeIntegration):

    response = requests.get('https://api.foursquare.com/v2/users/self/checkins', {
                            'oauth_token': activeIntegration.access_token, 'v': '20161212'})
    data = response.json()
    logging.info("%s %s %s" %
                 (activeIntegration.user.username, "Checkin History", data))


@shared_task
def foursquareDetails(activeIntegration):

    # get user profile
    response = requests.get('https://api.foursquare.com/v2/users/self',
                            {'oauth_token': activeIntegration.access_token, 'v': '20161212'})
    data = response.json()
    logging.info("%s %s %s" %
                 (activeIntegration.user.username, "User Profile", data))

    try:
        user_id = data['response']['user']['id']
        activeIntegration.external_user_id = user_id
        activeIntegration.save()
    except:
        logging.warning("Unable to parse User ID from response.")

    # get checkin history
    foursquareCheckinHistory.apply_async(args=[activeIntegration])


@shared_task
@login_required()
def receiveFoursquareOAuth(request):

    # parse CODE
    tempCode = request.GET['code']

    # send to CODE<-->Auth_Token URL
    if True:
        integration = get_object_or_404(Integration, name='Swarm')

        response = requests.get(integration.token_url, {"client_id": os.environ['FOURSQUARE_CLIENT_ID'],
                                                        "client_secret": os.environ['FOURSQUARE_CLIENT_SECRET'],
                                                        "grant_type": "authorization_code", "code": tempCode,
                                                        "redirect_uri": "https://eleos-core.herokuapp.com/receiveOAuth"})

        response = response.json()
        access_token = response['access_token']
        logging.info("%s %s %s" %
                     (request.user.username, integration.name, access_token))

    # Create new Link
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=request.user, integration=integration, access_token=access_token)

    # pull history
    if new and integration.name == 'Swarm':
        foursquareDetailsa.apply_async(args=[activeIntegration])

    # send back to integrations
    return redirect('/integrations')
