import os
import json
import requests
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .models import ActiveIntegration, Integration, Module


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
    timeOfPostback = event['timestamp']
    payload = event['postback']['payload']

    try:
        ai_fb = ActiveIntegration.objects.get(external_user_id=senderId)
    except:
        print "Unable to find User with external_user_id %s. (postback: '%s')" % (senderId, payload)
        sendMessenger(senderId, "I seem to have misplaced your User Account.  Can you please visit https://eleos-core.herokuapp.com/modules to get it sorted out?")

    print "Received postback for user %s with payload '%s' at %s" % (ai_fb.user, payload, timeOfPostback)

    if payload.startswith('activate_module_id_'):

        moduleId = payload.strip('activate_module_id_')
        try:
            module = Module.objects.get(id=moduleId)
        except:
            print "Invalid Module ID %s." % moduleId
            return

        if user in module.users.all():
            print "User already enabled this Module."
            sendMessenger(senderId, "You've already enabled this Module.")
        else:
            for integration in module.required_integrations.all():
                if user not in integration.users.all():
                    # User hasn't enabled all necessary permissions
                    sendMessenger(senderId, "You have not enabled all the necessary permissions for this Module.  Please visit https://eleos-core.herokuapp.com/integrations.")
            module.users.add(request.user)
            sendMessenger(senderId, ""+module.name+" successfully activated! "+module.intro_message)
    else:
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

    senderId = event['sender']['id']

    try:
        user = User.objects.get(username=event['optin']['ref'])
    except:
        print "Unable to fetch User."

    integration = Integration.objects.get(name='Facebook')
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=user, integration=integration)

    if not activeIntegration.external_user_id:
        activeIntegration.external_user_id = senderId
        activeIntegration.save()

    if new:
        # ONBOARDING
        sendMessenger(senderId, "Welcome to Eleos! We're here to serve you.  Please pick a Module to get started:")
        availableModules = Module.objects.all()
        messageData = {"recipient": {"id": senderId},
                       'message': {
                            'attachment': {
                                'type': "template",
                                'payload': {
                                    'template_type': "generic",
                                    'elements': []
                                    }}}}
        for module in availableModules:
            messageData['message']['attachment']['payload']['elements'].append({
                                                                            'title': module.name,
                                                                            'subtitle': module.description,
                                                                            'item_url': "https://eleos-core.herokuapp.com/modules",
                                                                            'image_url': module.image_url,
                                                                            'buttons': [{
                                                                                'type': "postback",
                                                                                'title': "Activate "+module.name,
                                                                                'payload': "activate_module_id_"+str(module.id),
                                                                            }]})

        callSendAPI(messageData)
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

                if 'optin' in event:
                    newMessengerUser(event)
                elif 'postback' in event:
                    receivedPostback(event)
                elif 'message' in event:
                    dispatch(event)
                elif 'read' in event:
                    try:
                        ai_fb = ActiveIntegration.objects.get(external_user_id=event['sender']['id'])
                        print "%s has read my message ID: %s." % (ai_fb.user, event['read']['watermark'])
                    except:
                        print "Message recevied from unknown User."
                else:
                    print "Webhook received unknown event: ", event

    return HttpResponse(status=201)
