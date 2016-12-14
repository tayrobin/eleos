import os
import json
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


def callSendAPI(messageData):

    url = "https://graph.facebook.com/v2.6/me/messages"

    response = request.post(url, json=messageData, qs={'access_token':os.environ['PAGE_ACCESS_TOKEN']})
    data = response.json()

    recipientId = data['recipient_id']
    messageId = data['message_id']

    print "Successfully sent generic message with id %s to recipient %s" % (messageId, recipientId)


def sendGenericMessage(recipientId, messageText):
    pass


def sendTextMessage(recipientId, messageText):

    messageData = dict()
    messageData['recipient'] = dict()
    messageData['message'] = dict()
    messageData['recipient']['id'] = recipientId
    messageData['message']['text'] = messageText

    callSendAPI(messageData)


def dispatch(event):

    senderId = event['sender']['id']
    recipientId = event['recipient']['id']
    timeOfMessage = event['timestamp']
    message = event['message']

    print "Received message for user %s and page %s at %s with message:" % (senderId, recipientId, timeOfMessage)
    print message

    messageId = message['mid']

    messageText = message['text']
    messageAttachments = message['attachments']

    if messageText:

        # If we receive a text message, check to see if it matches a keyword
        # and send back the example. Otherwise, just echo the text we received.

        if 'generic' in messageText:
            sendGenericMessage(senderId)

        else:
            sendTextMessage(senderId, messageText)

    elif messageAttachments:
        sendTextMessage(senderId, "Message with attachment received")


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

        for entry in data:
            pageId = entry['id']
            timeOfEvent = entry['time']

            for event in entry['messaging']:
                if event['message']:
                    dispatch(event)
                else:
                    print "Webhook received unknown event: ", event

    return HttpResponse(status=201)
