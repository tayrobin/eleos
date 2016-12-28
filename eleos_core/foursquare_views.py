import os
import json
import requests
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Integration, Module, ActiveIntegration, GiftedMoment
from .messenger_views import sendMessenger, callSendAPI


@csrf_exempt
def foursquareCheckin(request):

    print request.POST
    dataJson = json.loads(dict(request.POST)['checkin'][0])
    print "dataJson", dataJson

    swarmUserId = dataJson['user']['id']
    venueName = dataJson['venue']['name']

    try:
        print "@%s went to %s" % (swarmUserId, venueName)
    except:
        print "weird characters in venueName"

    facebook = Integration.objects.get(name='Facebook')
    swarm = Integration.objects.get(name='Swarm')

    # get Swarm ActiveIntegration
    try:
        ai_swarm = ActiveIntegration.objects.get(
            external_user_id=swarmUserId, integration=swarm)
    except:
        print "Unable to find ActiveIntegration for this User."
        return HttpResponse(status=201)

    # get FBM ActiveIntegration
    try:
        ai_facebook = ActiveIntegration.objects.get(
            user=ai_swarm.user, integration=facebook)
        print "Now have ActiveIntegrations for both Swarm and FBM for %s" % ai_facebook.user
    except:
        print "Looks like %s hasn't given permission for FBM." % ai_swarm.user
        return HttpResponse(status=201)

    giftedMoment = GiftedMoment.objects.filter(
        recipient=ai_swarm.user, fbm_message_id=None).first()

    # deliver Moment (or generic response)
    if giftedMoment:
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
                                        "url": giftedMoment.payload.deliverable_url,
                                        "messenger_extensions": True,
                                        "webview_height_ratio": "tall",
                                        "fallback_url": "https://eleos-core.herokuapp.com"
                                    },
                                    "buttons": [
                                        {
                                            "type": "postback",
                                            "title": "Now is not the right Moment",
                                            "payload": "bad_moment"
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
                                            "title": "Now is not the right Moment",
                                            "payload": "bad_moment"
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
            try:
            	messageId = callSendAPI(messageData)
            	#messageId = sendMessenger(recipientId=ai_facebook.external_user_id, messageText=message)
                if messageId:
                    if '.' and ':' in messageId:
                        messageId = messageId.split('.')[1].split(':')[0]
                    giftedMoment.fbm_message_id = messageId
                    giftedMoment.fbm_sent_status = True
                    giftedMoment.fbm_message_sent_at = timezone.now()
                    giftedMoment.save()
                else:
                    print "No messageId returned, delivery must have failed."
            except:
				print "Error calling callSendAPI()"
                return HttpResponse(status=201)
        else:
            print "messageData not successfully formed."
    else:
        try:
            sendMessenger(recipientId=ai_facebook.external_user_id,
                          messageText="Nice checkin at %s!" % venueName)
        except:
			print "Error calling sendMessenger()"
            return HttpResponse(status=201)

    return HttpResponse(status=201)


def foursquareDetails(activeIntegration):

    # get user profile
    response = requests.get('https://api.foursquare.com/v2/users/self',
                            {'oauth_token': activeIntegration.access_token, 'v': '20161212'})
    data = response.json()
    print activeIntegration.user.username, "User Profile", data

    try:
        user_id = data['response']['user']['id']
        activeIntegration.external_user_id = user_id
        activeIntegration.save()
    except:
        print "Unable to parse User ID from response."

    # get checkin history
    response = requests.get('https://api.foursquare.com/v2/users/self/checkins', {
                            'oauth_token': activeIntegration.access_token, 'v': '20161212'})
    data = response.json()
    print activeIntegration.user.username, "Checkin History", data


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
        print request.user.username, integration.name, access_token

    # Create new Link
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=request.user, integration=integration, access_token=access_token)

    # pull history
    if new and integration.name == 'Swarm':
        foursquareDetails(activeIntegration)

    # send back to integrations
    return redirect('/integrations')
