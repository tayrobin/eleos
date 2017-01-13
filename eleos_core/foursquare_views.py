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

            # add random delay for testing
            if random.random() > 0.70:
                delay = random.uniform(1.0, 10.0)
                logging.warning("delaying for %s seconds" % delay)
                time.sleep(delay)

            giftedMoment = random.choice(giftedMoments)
        else:
            try:
                sendMessenger.apply_async(kwargs={'recipientId': ai_facebook.external_user_id,
                                                  'messageText': "Nice checkin at %s!" % venueName})
            except:
                logging.warning("Error calling sendMessenger()")
                return HttpResponse(status=201)

    messageData = None

    if giftedMoment.payload.deliverable_url:
        # send as attachment
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
                                "title": '%(creator)s created a %(length)s minute %(context)s Moment for you:' % {'creator': giftedMoment.creator, 'length': giftedMoment.payload.length, 'context': giftedMoment.get_context_display()},
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
    else:
        # send as text
        message = '%(creator)s created a %(length)s minute %(context)s Moment for you:\n"%(endorsement)s"\n%(deliverable)s' % {
            'creator': giftedMoment.creator, 'length': giftedMoment.payload.length, 'context': giftedMoment.get_context_display(), 'endorsement': giftedMoment.endorsement, 'deliverable': giftedMoment.payload.deliverable}
        messageData = {
            "recipient": {
                "id": ai_facebook.external_user_id
            },
            "message": {
                "attachment": {
                    "type": "template",
                            "payload": {
                                "template_type": "button",
                                "text": message,
                                "buttons": [
                                    {
                                        "type": "postback",
                                        "title": "Not a good Moment",
                                        "payload": "bad_moment_" + str(giftedMoment.id)
                                    },
                                    {
                                        "type": "postback",
                                        "title": "Thank %(creator)s" % {'creator': giftedMoment.creator},
                                        "payload": "thank_%(creator)s" % {'creator': giftedMoment.creator}
                                    }
                                ]
                            }
                }
            }
        }

        if messageData:
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
        else:
            logging.warning("messageData not successfully formed.")


@shared_task
@csrf_exempt
def foursquareCheckin(request):

    logging.info(request.POST)
    dataJson = json.loads(dict(request.POST)['checkin'][0])
    logging.info("dataJson: %s" % dataJson)

    swarmUserId = dataJson['user']['id']
    venueName = dataJson['venue']['name']

    try:
        logging.info("@%s went to %s" % (swarmUserId, venueName))
    except:
        logging.warning("weird characters in venueName")

    facebook = Integration.objects.get(name='Facebook')
    swarm = Integration.objects.get(name='Swarm')

    # get Swarm ActiveIntegration
    try:
        ai_swarm = ActiveIntegration.objects.get(
            external_user_id=swarmUserId, integration=swarm)
    except:
        logging.warning("Unable to find ActiveIntegration for this User.")
        return HttpResponse(status=201)

    # get FBM ActiveIntegration
    try:
        ai_facebook = ActiveIntegration.objects.get(
            user=ai_swarm.user, integration=facebook)
        logging.info(
            "Now have ActiveIntegrations for both Swarm and FBM for %s" % ai_facebook.user)
    except:
        logging.warning(
            "Looks like %s hasn't given permission for FBM." % ai_swarm.user)
        return HttpResponse(status=201)

    # asynchronously check for and deliver a Moment
    giveGiftedMoment.apply_async(args=[ai_facebook.user.id])

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
