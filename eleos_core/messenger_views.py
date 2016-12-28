import os
import json
import random
import requests
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ActiveIntegration, Integration, Module, GiftedMoment


def callSendAPI(messageData):

    url = "https://graph.facebook.com/v2.6/me/messages"

    response = requests.post(url, json=messageData, params={
                             'access_token': os.environ['PAGE_ACCESS_TOKEN']})
    data = response.json()

    recipientId = data['recipient_id']
    messageId = data['message_id']

    print "Successfully sent generic message with id %s to recipient %s" % (messageId, recipientId)

    return messageId


def sendMessenger(recipientId, messageText):

    messageData = {'recipient': {'id': recipientId},
                   'message': {'text': messageText}}

    messageId = callSendAPI(messageData)

    return messageId


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
            messageData['message']['attachment']['payload'][
                'elements'][i]['buttons'][0]['title'] = "Deactivate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][
                0]['payload'] = "deactivate_module_id_ " + str(availableModules[i].id)
        else:
            messageData['message']['attachment']['payload'][
                'elements'][i]['buttons'][0]['title'] = "Activate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][
                0]['payload'] = "activate_module_id_ " + str(availableModules[i].id)

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
            messageData['message']['attachment']['payload'][
                'elements'][i]['buttons'][0]['title'] = "Deactivate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0][
                'payload'] = "deactivate_integration_id_ " + str(availableIntegrations[i].id)
        else:
            messageData['message']['attachment']['payload'][
                'elements'][i]['buttons'][0]['title'] = "Activate"
            messageData['message']['attachment']['payload']['elements'][i]['buttons'][0][
                'payload'] = "activate_integration_id_ " + str(availableIntegrations[i].id)

    callSendAPI(messageData)


def receivedPostback(event):

    senderId = event['sender']['id']
    timeOfPostback = event['timestamp']
    payload = event['postback']['payload']

    try:
        fb = Integration.objects.get(name='Facebook')
        ai_fb = ActiveIntegration.objects.get(
            external_user_id=senderId, integration=fb)
    except:
        print "Unable to find User with external_user_id %s. (postback: '%s')" % (senderId, payload)
        sendMessenger(
            senderId, "I seem to have misplaced your User Account.  Can you please visit https://eleos-core.herokuapp.com/modules to get it sorted out?")
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
                    sendMessenger(
                        senderId, "You have not enabled all the necessary permissions for this Module.  Please visit https://eleos-core.herokuapp.com/integrations.")
                    return
            module.users.add(ai_fb.user)
            sendMessenger(senderId, "" + module.name +
                          " successfully activated! " + module.intro_message)
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
            sendMessenger(
                senderId, "This Module is currently inactive for you.")
            return
        else:
            module.users.remove(ai_fb.user)
            sendMessenger(senderId, "" + module.name +
                          " successfully deactivated.")
            return
    elif payload.startswith('activate_integration_id_'):
        integrationId = payload.strip('activate_integration_id_')
        try:
            integration = Integration.objects.get(id=integrationId)
        except:
            print "Invalid Integration ID %s." % integrationId
            return

        sendMessenger(senderId, "Please visit: " +
                      "https://eleos-core.herokuapp.com/sendOAuth/" + integration.name)
        return
    elif payload.startswith('deactivate_integration_id_'):

        integrationId = payload.strip('deactivate_integration_id_')
        try:
            integration = Integration.objects.get(id=integrationId)
        except:
            print "Invalid Integration ID %s." % integrationId
            return
        try:
            ai = ActiveIntegration.objects.get(
                user=ai_fb.user, integration=integration)
        except:
            sendMessenger(
                senderId, "This Integration is currently inactive for you.")
            return

        ai.delete()

        sendMessenger(senderId, "" + integration.name +
                      " successfully deactivated.")
        return
    elif payload == 'show_modules':
        showModules(senderId, ai_fb.user)
    elif payload == 'show_integrations':
        showIntegrations(senderId, ai_fb.user)
    elif payload == 'bad_moment':
        sendMessenger(
            senderId, "Apologies.  I'll save this for a better time.")
        return
    elif payload.startswith('thank_'):
        username = payload.strip('thank_')
        sendMessenger(senderId, "Fantastic!  I'll let %(username)s know." % {
                      'username': username})
    else:
        sendMessenger(senderId, "Postback called")
        return


def sendHelpMessage(recipientId, user):

    messageData = {
        "recipient": {
            "id": recipientId
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": "Sorry, I didn't understand that.  I'm still being programmed!  Here are some things I can do:",
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "Show Modules",
                            "payload": "show_modules"
                        },
                        {
                            "type": "postback",
                            "title": "Show Integrations",
                            "payload": "show_integrations"
                        }
                    ]
                }
            }
        }
    }

    callSendAPI(messageData)


def dispatch(event):

    senderId = event['sender']['id']

    try:
        fb = Integration.objects.get(name='Facebook')
        ai = ActiveIntegration.objects.get(
            external_user_id=senderId, integration=fb)
    except:
        ai = None

    message = event['message']

    print "Received message from user %s:" % (ai.user if ai else senderId)
    print message

    messageId = message['mid']

    if 'text' in message:

        if 'modules' in message['text'].lower() and ai:
            showModules(senderId, ai.user)
        elif 'integrations' in message['text'].lower() and ai:
            showIntegrations(senderId, ai.user)
        elif 'thanks' in message['text'].lower() and ai:
            sendMessenger(senderId, random.choice(
                ["Happy to help.", "My pleasure.", "Anything I can do to help.", "You're welcome!", "My what good manners you have!"]))
        else:
            sendHelpMessage(senderId, ai.user)

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
        sendMessenger(
            senderId, "Welcome to Eleos! We're here to serve you.  Please pick a Module to get started:")
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
                        ai_fb = ActiveIntegration.objects.get(
                            external_user_id=event['sender']['id'])
                        print "%s has read my message ID: %s." % (ai_fb.user, event['read']['watermark'])
                        giftedMoments = GiftedMoment.objects.filter(
                            fbm_message_id=event['read']['watermark'])
                        if len(giftedMoments) > 0:
                            if len(giftedMoments) > 1:
                                print "More than 1 GiftedMoment with this FBM Message ID found."
                                print giftedMoments
                            else:
                                giftedMoment = giftedMoments[0]
                                giftedMoment.fbm_read_status = True
                                giftedMoment.fbm_message_read_at = timezone.now()
                                giftedMoment.save()
                        else:
                            print "No GiftedMoment with this FBM Message ID found."
                    except:
                        print "Message recevied from unknown User."
                else:
                    print "Webhook received unknown event: ", event

    return HttpResponse(status=201)


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

    response = requests.get(integration.token_url, {"client_id": os.environ['FACEBOOK_APP_ID'],
                                                    "client_secret": os.environ['FACEBOOK_APP_SECRET'],
                                                    "code": tempCode,
                                                    "redirect_uri": "https://eleos-core.herokuapp.com/receive_facebook_oauth"})

    response = response.json()
    access_token = response['access_token']
    print request.user.username, integration.name, access_token

    # Create new Link
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=request.user, integration=integration)
    if not activeIntegration.access_token:
        activeIntegration.access_token = access_token
        activeIntegration.save()

    # send back to integrations
    return redirect('/integrations')
