import os
import json
import logging
import requests
from celery import shared_task
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)

slackTestToken = os.environ["SLACK_TEST_TOKEN"]
requestedMomentsChannel = "C3Y8PFDCG"


@shared_task
def sendTextToSlack(text):

    response = requests.post(
        os.environ["SLACK_WEBHOOK_URL"], json={"text":text})
        #'https://slack.com/api/chat.postMessage', json={"text":text, "token":slackTestToken, "channel":requestedMomentsChannel})

    if 'error' in response:
        logging.warning("Error sending message to Slack: %s" % response.text)
    else:
        logging.info("Successfully sent message to Slack.")


@shared_task
def sendPayloadToSlack(payload):

    if type(payload) == dict:
        response = requests.post( os.environ["SLACK_WEBHOOK_URL"], json=payload)
            #'https://slack.com/api/chat.postMessage', params=payload, headers={"Content-Type":"application/json"})
    else:
        raise TypeError("Provided payload is not a dictionary.")

    if 'error' in response:
        logging.warning(response)
        logging.warning("Error sending message to Slack: %s" % response.text)
    else:
        logging.info("Successfully sent message to Slack.")


@shared_task
def sendContentRequestToSlack(text):

    payload = {
        "attachments": json.dumps(
            [{
                "text": text,
                "fallback": "A User requested content.",
                "callback_id": "content_request",
                "color": "#5cb85c",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "respond",
                        "text": "Respond",
                        "type": "button",
                        "value": "respond",
                        "style": "primary"
                    },
                    {
                        "name": "report",
                        "text": "Report",
                        "style": "danger",
                        "type": "button",
                        "value": "report",
                        "confirm": {
                            "title": "Are you sure?",
                            "text": "This will ban the User from Eleos.",
                            "ok_text": "Yes",
                            "dismiss_text": "No"
                        }
                    }
                ]
            }
        ]), "token":slackTestToken, "channel":requestedMomentsChannel
    }

    sendPayloadToSlack.apply_async(kwargs={"payload":payload})


@csrf_exempt
def receiveSlackWebhook(request):

    if request.method == "POST":

        incomingPost = request.POST
        logging.info("POST:", incomingPost)

        logging.info( "Headers:", request.META )

        payloadString = incomingPost['payload']
        logging.info( "payloadString:", payloadString )

        inputs = json.loads(payloadString)
        logging.info( "json POST['payload'][0]:", inputs )

    else:
        logging.info("GET:", request.GET)

    return HttpResponse('OK')