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
        fb = Integration.objects.get(name='Facebook')
        ai_fb = ActiveIntegration.objects.get(external_user_id=senderId, integration=fb)
    except:
        print "Unable to find User with external_user_id %s. (postback: '%s')" % (senderId, payload)
        sendMessenger(senderId, "I seem to have misplaced your User Account.  Can you please visit https://eleos-core.herokuapp.com/modules to get it sorted out?")
        return

    print "Received postback for user %s with payload '%s' at %s" % (ai_fb.user, payload, timeOfPostback)

    if payload.startswith('activate_module_id_'):

        moduleId = payload.strip('activate_module_id_')
        try:
            module = Module.objects.get(id=moduleId)
        except:
            print "Invalid Module ID %s." % moduleId
            return

        if ai_fb.user in module.users.all():
            print "User already enabled this Module."
            sendMessenger(senderId, "You've already enabled this Module.")
            return
        else:
            for integration in module.required_integrations.all():
                if ai_fb.user not in integration.users.all():
                    # User hasn't enabled all necessary permissions
                    sendMessenger(senderId, "You have not enabled all the necessary permissions for this Module.  Please visit https://eleos-core.herokuapp.com/integrations.")
                    return
            module.users.add(ai_fb.user)
            sendMessenger(senderId, ""+module.name+" successfully activated! "+module.intro_message)
            return
    elif payload.startswith('deactivate_module_id_'):

        moduleId = payload.strip('deactivate_module_id_')
        try:
            module = Module.objects.get(id=moduleId)
        except:
            print "Invalid Module ID %s." % moduleId
            return

        if ai_fb.user not in module.users.all():
            print "User had not enabled this Module."
            sendMessenger(senderId, "This Module is currently inactive for you.")
            return
        else:
            module.users.remove(ai_fb.user)
            sendMessenger(senderId, ""+module.name+" successfully deactivated.")
            return
    elif payload.startswith('activate_integration_id_'):
        integrationId = payload.strip('activate_integration_id_')
        try:
            integration = Integration.objects.get(id=integrationId)
        except:
            print "Invalid Integration ID %s." % integrationId
            return

        sendMessenger(senderId, "Please visit: "+"https://eleos-core.herokuapp.com/sendOAuth/"+integration.name)
        return
    elif payload.startswith('deactivate_integration_id_'):
        
        integrationId = payload.strip('deactivate_integration_id_')
        try:
            integration = Integration.objects.get(id=integrationId)
        except:
            print "Invalid Integration ID %s." % integrationId
            return
        try:
            ai = ActiveIntegration.objects.get(user=ai_fb.user, integration=integration)
        except:
            sendMessenger(senderId, "This Integration is currently inactive for you.")
            return

        ai.delete()

        sendMessenger(senderId, ""+integration.name+" successfully deactivated.")
        return
    else:
        sendMessenger(senderId, "Postback called")
        return


def showModules(recipientId, user):

    availableModules = Module.objects.all()
    messageData = {"recipient": {"id": recipientId},
                   'message': {
                        'attachment': {
                            'type': "template",
                            'payload': {
                                'template_type': "generic",
                                'elements': []
                                }}}}
    for i in range(len(availableModules)):
        messageData['message']['attachment']['payload']['elements'].append({
                                                                        'title': availableModules[i].name,
                                                                        'subtitle': availableModules[i].description,
                                                                        'item_url': "https://eleos-core.herokuapp.com/modules",
                                                                        'image_url': availableModules[i].image_url,
                                                                        'buttons': [{
                                                                            'type': "postback",
                                                                            'title': "",
                                                                            'payload': "",
                                                                        }]})
        if user in availableModules[i].users.all():
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['title'] = "Deactivate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['payload'] = "deactivate_module_id_ "+str(availableModules[i].id)
        else:
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['title'] = "Activate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['payload'] = "activate_module_id_ "+str(availableModules[i].id)

    callSendAPI(messageData)


def showIntegrations(recipientId, user):
    
    availableIntegrations = Integration.objects.all()
    messageData = {"recipient": {"id": recipientId},
                   'message': {
                        'attachment': {
                            'type': "template",
                            'payload': {
                                'template_type': "generic",
                                'elements': []
                                }}}}
    for i in range(len(availableIntegrations)):
        messageData['message']['attachment']['payload']['elements'].append({
                                                                        'title': availableIntegrations[i].name,
                                                                        'subtitle': availableIntegrations[i].description,
                                                                        'item_url': "https://eleos-core.herokuapp.com/integrations",
                                                                        'image_url': availableIntegrations[i].image_url,
                                                                        'buttons': [{
                                                                            'type': "postback",
                                                                            'title': "",
                                                                            'payload': "",
                                                                        }]})
        if user in availableIntegrations[i].users.all():
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['title'] = "Deactivate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['payload'] = "deactivate_integration_id_ "+str(availableIntegrations[i].id)
        else:
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['title'] = "Activate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0]['payload'] = "activate_integration_id_ "+str(availableIntegrations[i].id)

    callSendAPI(messageData)


def dispatch(event):

    senderId = event['sender']['id']

    try:
        fb = Integration.objects.get(name='Facebook')
        ai = ActiveIntegration.objects.get(external_user_id=senderId, integration=fb)
    except:
        ai = None

    message = event['message']

    print "Received message from user %s:" % (ai.user if ai else senderId)
    print message

    messageId = message['mid']

    if 'text' in message:

        if 'generic' in message['text'].lower():
            sendGenericMessage(senderId)
        elif 'show modules' in message['text'].lower() and ai:
            showModules(senderId, ai.user)
        elif 'show integrations' in message['text'].lower() and ai:
            showIntegrations(senderId, ai.user)
        else:
            sendMessenger(senderId, message['text'])

    elif 'attachments' in message:
        sendMessenger(senderId, "Message with attachment received")


def newMessengerUser(event):

    senderId = event['sender']['id']

    try:
        user = User.objects.get(username=event['optin']['ref'])
    except:
        user = None
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
        showModules(senderId, user)
        return
    else:
        # already existed
        sendMessenger(senderId, "We meet again..")
        return


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
