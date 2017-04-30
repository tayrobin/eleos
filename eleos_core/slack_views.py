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
SLACK_WEBHOOK_URL_REQUESTED_MOMENTS = os.environ["SLACK_WEBHOOK_URL_REQUESTED_MOMENTS"]
SLACK_WEBHOOK_URL_MOMENT_BUILDER = os.environ["SLACK_WEBHOOK_URL_MOMENT_BUILDER"]


@shared_task
def sendPayloadToSlack(payload, channel="requested_moments"):

    if channel == "moment_builder":
        webhook_url = SLACK_WEBHOOK_URL_MOMENT_BUILDER
    else:
        webhook_url = SLACK_WEBHOOK_URL_REQUESTED_MOMENTS


    if not isinstance(payload, dict):
        raise TypeError("Provided payload is not a dictionary.")
    else:
        response = requests.post(webhook_url, json=payload)
        #'https://slack.com/api/chat.postMessage', params=payload, headers={"Content-Type":"application/json"})


    if 'error' in response:
        logging.warning(response)
        logging.warning("Error sending message to Slack: %s" % response.text)
    else:
        logging.info("Successfully sent message to Slack.")


@shared_task
def sendTextToSlack(text, channel="requested_moments"):

    sendPayloadToSlack(payload={"text":text}, channel=channel)


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
