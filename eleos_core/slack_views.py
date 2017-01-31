import os
import logging
import requests
from celery import shared_task

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)


@shared_task
def sendTextToSlack(text):

    response = requests.post(
        os.environ["SLACK_WEBHOOK_URL"], json={"text": text})

    if response.status_code == 200:
        logging.info("Successfully sent message to Slack.")
    else:
        logging.warning("Error sending message to Slack: %s" % response.text)


@shared_task
def sendPayloadToSlack(payload):

    if type(payload) == dict:
        response = requests.post(os.environ["SLACK_WEBHOOK_URL"], json=payload)
    else:
        raise TypeError("Provided payload is not a dictionary.")

    if response.status_code == 200:
        logging.info("Successfully sent message to Slack.")
    else:
        logging.warning("Error sending message to Slack: %s" % response.text)
