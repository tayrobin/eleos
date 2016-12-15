import os
import json
import requests
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .models import ActiveIntegration, Integration


def callSendAPI(messageData):

    url = "https://graph.facebook.com/v2.6/me/messages"

    response = requests.post(url, json=messageData, params={
                             'access_token': os.environ['PAGE_ACCESS_TOKEN']})
    data = response.json()

    recipientId = data['recipient_id']
    messageId = data['message_id']

    print "Successfully sent generic message with id %s to recipient %s" % (messageId, recipientId)


def sendMessenger(recipientId, messageText):

    messageData = {'recipient': {'id': recipientId},
                   'message': {'text': messageText}}

    callSendAPI(messageData)


def sendGenericMessage(recipientId):

    messageData = {
        'recipient': {
            'id': recipientId
        },
        'message': {
            'attachment': {
                'type': "template",
                'payload': {
                    'template_type': "generic",
                    'elements': [{
                        'title': "rift",
                        'subtitle': "Next-generation virtual reality",
                        'item_url': "https://www.oculus.com/en-us/rift/",
                        'image_url': "http://messengerdemo.parseapp.com/img/rift.png",
                        'buttons': [{
                            'type': "web_url",
                            'url': "https://www.oculus.com/en-us/rift/",
                            'title': "Open Web URL"
                        }, {
                            'type': "postback",
                            'title': "Call Postback",
                            'payload': "Payload for first bubble",
                        }],
                    }, {
                        'title': "touch",
                        'subtitle': "Your Hands, Now in VR",
                        'item_url': "https://www.oculus.com/en-us/touch/",
                        'image_url': "http://messengerdemo.parseapp.com/img/touch.png",
                        'buttons': [{
                            'type': "web_url",
                            'url': "https://www.oculus.com/en-us/touch/",
                            'title': "Open Web URL"
                        }, {
                            'type': "postback",
                            'title': "Call Postback",
                            'payload': "Payload for second bubble",
                        }]
                    }]
                }
            }
        }
    }

    callSendAPI(messageData)


def receivedPostback(event):

    senderId = event['sender']['id']
    recipientId = event['recipient']['id']
    timeOfPostback = event['timestamp']

    payload = event['postback']['payload']

    print "Received postback for user %s and page %s with payload '%s' at %s" % (senderId, recipientId, payload, timeOfPostback)

    sendMessenger(senderId, "Postback called")


def dispatch(event):

    senderId = event['sender']['id']

    try:
        ai = ActiveIntegration.objects.get(external_user_id=senderId)
    except:
        ai = None

    recipientId = event['recipient']['id']
    timeOfMessage = event['timestamp']
    message = event['message']

    print "Received message from user %s:" % (ai.user if ai else senderId)
    print message

    messageId = message['mid']

    if 'text' in message:

        if 'generic' in message['text']:
            sendGenericMessage(senderId)

        else:
            sendMessenger(senderId, message['text'])

    elif 'attachments' in message:
        sendMessenger(senderId, "Message with attachment received")


def newMessengerUser(event):

    recipientId = event['recipient']['id']
    senderId = event['sender']['id']
    user = get_object_or_404(User, username=event['optin']['ref'])
    integration = Integration.objects.get(name='Facebook')
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=user, integration=integration)
    if not activeIntegration.external_user_id:
        activeIntegration.external_user_id = senderId
        activeIntegration.save()

    if new:
        # get an access_token ??
        sendMessenger(senderId, "Welcome!")
    else:
        # already existed
        sendMessenger(senderId, "We meet again..")


@csrf_exempt
def receiveMessengerWebhook(request):

    if request.method == 'GET':
        data = request.GET
        print "data", data

        if 'hub.verify_token' in data:
            verify_token = data['hub.verify_token']
            if verify_token != "speak_friend_and_enter":
                return HttpResponse(status=403)

        if 'hub.challenge' in data:
            challenge = data['hub.challenge']
            return HttpResponse(challenge)
        else:
            return HttpResponse(status=403)

    elif request.method == 'POST':
        data = json.loads(request.body)

        for entry in data['entry']:
            pageId = entry['id']
            timeOfEvent = entry['time']

            for event in entry['messaging']:

                if 'message' in event:
                    dispatch(event)
                elif 'postback' in event:
                    receivedPostback(event)
                elif 'optin' in event:
                    newMessengerUser(event)
                elif 'read' in event:
                    try:
                        ai_fb = ActiveIntegration.objects.get(external_user_id=event['sender']['id'])
                        print "%s has read my message ID: %s." % (ai_fb.user, event['read']['watermark'])
                    except:
                        print "Message recevied from unknown User."
                else:
                    print "Webhook received unknown event: ", event

    return HttpResponse(status=201)
