import os
import json
import random
import logging
import requests
from celery import shared_task
from django.utils import timezone
from django.http import HttpResponse
from .slack_views import sendTextToSlack
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ActiveIntegration, Integration, Module, GiftedMoment

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)


@shared_task
def callSendAPI(messageData):

    url = "https://graph.facebook.com/v2.6/me/messages"

    response = requests.post(url, json=messageData, params={
        'access_token': os.environ['PAGE_ACCESS_TOKEN']})
    data = response.json()

    try:
        recipientId = data['recipient_id']
        messageId = data['message_id']
        logging.info("Successfully sent generic message with id %s to recipient %s" % (
            messageId, recipientId))
    except:
        recipientId = None
        messageId = None
        logging.warning(data)

    return messageId


@shared_task
def sendMessenger(recipientId, messageText):

    messageData = {'recipient': {'id': recipientId},
                   'message': {'text': messageText}}

    messageId = callSendAPI.apply_async(args=[messageData])

    return messageId


@shared_task
def showModules(recipientId, user):

    if type(user) is int:
        user = get_object_or_404(User, pk=user)

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

    callSendAPI.apply_async(args=[messageData])


@shared_task
def showIntegrations(recipientId, user):

    if type(user) is int:
        user = get_object_or_404(User, pk=user)

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

    callSendAPI.apply_async(args=[messageData])


@shared_task
def receivedPostback(event):

    senderId = event['sender']['id']
    timeOfPostback = event['timestamp']
    payload = event['postback']['payload']

    try:
        fb = Integration.objects.get(name='Facebook')
        ai_fb = ActiveIntegration.objects.get(
            external_user_id=senderId, integration=fb)
    except:
        logging.warning("Unable to find User with external_user_id %s. (postback: '%s')" % (
            senderId, payload))
        sendMessenger.apply_async(
            args=[senderId, "I seem to have misplaced your User Account.  Can you please visit https://eleos-core.herokuapp.com/modules to get it sorted out?"])
        return

    logging.info("Received postback for user %s with payload '%s' at %s" %
                 (ai_fb.user, payload, timeOfPostback))

    if payload.startswith('activate_module_id_'):

        moduleId = payload.strip('activate_module_id_')
        try:
            module = Module.objects.get(id=moduleId)
        except:
            logging.warning("Invalid Module ID %s." % moduleId)
            return

        if ai_fb.user in module.users.all():
            logging.warning("User already enabled this Module.")
            sendMessenger.apply_async(
                args=[senderId, "You've already enabled this Module."])
            return
        else:
            for integration in module.required_integrations.all():
                if ai_fb.user not in integration.users.all():
                    # User hasn't enabled all necessary permissions
                    sendMessenger.apply_async(
                        args=[senderId, "You have not enabled all the necessary permissions for this Module.  Please visit https://eleos-core.herokuapp.com/integrations."])
                    return
            module.users.add(ai_fb.user)
            sendMessenger.apply_async(args=[senderId, "" + module.name +
                                            " successfully activated! " + module.intro_message])
            return
    elif payload.startswith('deactivate_module_id_'):

        moduleId = payload.strip('deactivate_module_id_')
        try:
            module = Module.objects.get(id=moduleId)
        except:
            logging.warning("Invalid Module ID %s." % moduleId)
            return

        if ai_fb.user not in module.users.all():
            logging.warning("User had not enabled this Module.")
            sendMessenger.apply_async(
                args=[senderId, "This Module is currently inactive for you."])
            return
        else:
            module.users.remove(ai_fb.user)
            sendMessenger.apply_async(args=[senderId, "" + module.name +
                                            " successfully deactivated."])
            return
    elif payload.startswith('activate_integration_id_'):
        integrationId = payload.strip('activate_integration_id_')
        try:
            integration = Integration.objects.get(id=integrationId)
        except:
            logging.warning("Invalid Integration ID %s." % integrationId)
            return

        sendMessenger.apply_async(args=[senderId, "Please visit: " +
                                        "https://eleos-core.herokuapp.com/sendOAuth/" + integration.name])
        return
    elif payload.startswith('deactivate_integration_id_'):

        integrationId = payload.strip('deactivate_integration_id_')
        try:
            integration = Integration.objects.get(id=integrationId)
        except:
            logging.warning("Invalid Integration ID %s." % integrationId)
            return
        try:
            ai = ActiveIntegration.objects.get(
                user=ai_fb.user, integration=integration)
        except:
            sendMessenger.apply_async(
                args=[senderId, "This Integration is currently inactive for you."])
            return

        ai.delete()

        sendMessenger.apply_async(args=[senderId, "" + integration.name +
                                        " successfully deactivated."])
        return
    elif payload == 'show_modules':
        showModules.apply_async(args=[senderId, ai_fb.user.id])
    elif payload == 'show_integrations':
        showIntegrations.apply_async(args=[senderId, ai_fb.user.id])
    elif payload.startswith('bad_moment_'):
        sendMessenger.apply_async(
            args=[senderId, "Apologies.  I'll save this for a better time."])

        # fetch original GiftedMoment by FBM Message ID and nullify sent status
        giftedMomentId = payload.strip('bad_moment_')
        g = get_object_or_404(GiftedMoment, pk=giftedMomentId)
        g.fbm_message_id = None
        g.fbm_sent_status = False
        g.save()
        logging.info("GiftedMoment delivery status reset.")
        return
    elif payload.startswith('thank_'):
        username = payload.strip('thank_')
        sendMessenger.apply_async(args=[senderId, "Fantastic!  I'll let %(username)s know." % {
                                  'username': username}])
    else:
        sendMessenger.apply_async(args=[senderId, "Postback called"])
        return


@shared_task
def sendHelpMessage(recipientId, user):

    if type(user) is int:
        user = get_object_or_404(User, pk=user)

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

    callSendAPI.apply_async(args=[messageData])


@shared_task
def messengerLocationAttachment(attachment, senderId, username):

    # parse attributes
    lat = attachment['payload']['coordinates']['lat']
    lng = attachment['payload']['coordinates']['long']
    url = attachment['url']
    placeName = attachment['title']

    # geocode with Foursquare

    # ping Slack
    slackMessage = "%(username)s has requested content at <%(url)s|%(placeName)s - (%(lat)s,%(lng)s)>!" % {
        'username': username, 'placeName': placeName, 'url': url, 'lat': lat, 'lng': lng}
    sendTextToSlack.apply_async(kwargs={'text': slackMessage})

    # respond to user
    sendMessenger.apply_async(
        args=[senderId, "I see you're at %s!  Give me just a minute to find you something awesome." % placeName])


@shared_task
def dispatch(event):

    senderId = event['sender']['id']
    message = event['message']
    logging.info(message)

    fb = Integration.objects.get(name='Facebook')

    try:
        ai = ActiveIntegration.objects.get(
            external_user_id=senderId, integration=fb)
    except:
        ai = None
        logging.warning(
            "Unkown FBM User (%s). Sending generic login message." % senderId)
        sendMessenger.apply_async(
            args=[senderId, "Hi there!\nI'm not sure we've yet been acquainted.  Eleos works through Integrations with services you already use.  Would you mind visiting https://eleos-core.herokuapp.com to get set up with an Eleos account?\nI look forward to serving you!"])
        return

    logging.info("Received message from user %s:" %
                 (ai.user if ai else senderId))

    messageId = message['mid']

    if 'text' in message:

        if 'modules' in message['text'].lower() and ai:
            showModules.apply_async(args=[senderId, ai.user.id])
        elif 'integrations' in message['text'].lower() and ai:
            showIntegrations.apply_async(args=[senderId, ai.user.id])
        elif 'thank' in message['text'].lower() and ai:
            sendMessenger.apply_async(args=[senderId, random.choice(
                ["Happy to help.", "My pleasure.", "Anything I can do to help.", "You're welcome!", "My what good manners you have!"])])
        else:
            sendHelpMessage.apply_async(args=[senderId, ai.user.id])

    elif 'attachments' in message:

        for attachment in message['attachments']:
            if 'type' in attachment and attachment['type'] == 'location':
                messengerLocationAttachment.apply_async(
                    kwargs={'attachment': attachment, 'senderId': senderId, 'username': ai.user.username})
            else:
                # send basic response
                sendMessenger.apply_async(
                    args=[senderId, "Message with attachment received"])


@shared_task
def newMessengerUser(event):

    senderId = event['sender']['id']

    try:
        user = User.objects.get(username=event['optin']['ref'])
        logging.info("New FBM User %s." % user)
    except:
        user = None
        logging.warning("Unable to fetch User.")

    integration = Integration.objects.get(name='Facebook')
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=user, integration=integration)

    if not activeIntegration.external_user_id:
        logging.info("Filling in missing external_user_id (%s) for %s." %
                     (senderId, activeIntegration.user))
        activeIntegration.external_user_id = senderId
        activeIntegration.save()

    if new:
        # ONBOARDING
        sendMessenger.apply_async(
            args=[senderId, "Welcome to Eleos! We're here to serve you.  Please pick a Module to get started:"])
        showModules.apply_async(args=[senderId, user.id])
        return
    else:
        # already existed
        sendMessenger.apply_async(args=[senderId, "We meet again.."])
        return


@shared_task
def updatedGiftedMomentReadStatus(event):

    giftedMoments = GiftedMoment.objects.filter(
        fbm_message_id=event['read']['watermark'])
    if len(giftedMoments) > 0:
        if len(giftedMoments) > 1:
            logging.warning(
                "More than 1 GiftedMoment with this FBM Message ID found.")
            logging.warning(giftedMoments)
        else:
            giftedMoment = giftedMoments[0]
            giftedMoment.fbm_read_status = True
            giftedMoment.fbm_message_read_at = timezone.now()
            giftedMoment.save()
    else:
        logging.warning("No GiftedMoment with this FBM Message ID found.")


@csrf_exempt
def receiveMessengerWebhook(request):

    if request.method == 'GET':
        data = request.GET
        logging.info("data %s" % data)

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
                    newMessengerUser.apply_async(args=[event])
                elif 'postback' in event:
                    receivedPostback.apply_async(args=[event])
                elif 'message' in event:
                    dispatch.apply_async(args=[event])
                elif 'read' in event:
                    # updated GiftedMoment
                    updatedGiftedMomentReadStatus.apply_async(args=[event])
                else:
                    logging.warning(
                        "Webhook received unknown event: %s" % event)

    return HttpResponse(status=201)


@login_required()
def receiveFacebookOAuth(request):

    if request.method == 'GET':
        logging.info("GET %s" % request.GET)
    elif request.method == 'POST':
        logging.info("POST %s" % request.POST)
        logging.info("DATA %s" % request.body)

    # parse CODE
    tempCode = request.GET['code']

    # send to CODE<-->Auth_Token URL
    integration = get_object_or_404(Integration, name='Facebook')

    response = requests.get(integration.token_url, {"client_id": os.environ['FACEBOOK_APP_ID'],
                                                    "client_secret": os.environ['FACEBOOK_APP_SECRET'],
                                                    "code": tempCode,
                                                    "redirect_uri": "https://eleos-core.herokuapp.com/receive_facebook_oauth"})

    response = response.json()
    logging.info("FBM Code-->Auth Response: %s" % response)
    access_token = response['access_token']
    logging.info("%s %s %s" %
                 (request.user.username, integration.name, access_token))

    # Create new Link
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=request.user, integration=integration)
    if not activeIntegration.access_token:
        activeIntegration.access_token = access_token
        activeIntegration.save()

    # send back to integrations
    return redirect('/integrations')
