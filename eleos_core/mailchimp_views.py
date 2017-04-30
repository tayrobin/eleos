import os
import logging

from celery import shared_task
from mailchimp3 import MailChimp

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)


MAILCHIMP_API_KEY = os.environ["MAILCHIMP_API_KEY"]
MAILCHIMP_USERNAME = os.environ["MAILCHIMP_USERNAME"]
list_id = "66add092d7"


client = MailChimp(MAILCHIMP_USERNAME, MAILCHIMP_API_KEY)


@shared_task
def subscribe_user_to_list(email, list_id="66add092d7", FNAME=None, LNAME=None):

    try:
        client.lists.members.create(list_id, {
            "email_address": email,
            "status": "subscribed",
            "merge_fields": {
                "FNAME": FNAME,
                "LNAME": LNAME
            }
        })
    except:
        logging.warning("Unable to add %s to Mailchimp List ID: %s." % (email, list_id))


def user_in_list(email, list_id="66add092d7"):

    subscribers = client.lists.members.all(list_id, fields="members.email_address")

    logging.info(subscribers)

    matched_emails = [person.get("email_address") for person in subscribers.get("members") if person.get("email_address") == email]

    logging.info("Matched Emails: %s" % matched_emails)

    if matched_emails != []:
        if len(matched_emails) == 1:
            logging.info("Matching user found.")
            return True
        else:
            logging.warning("Multiple matching users found.")
            return True
    else:
        logging.info("No matching users found for %s." % email)
        return False


@shared_task
def handle_user_email(email, FNAME=None, LNAME=None):

    if user_in_list(email):
        logging.info("User already in list, not doing anything for now.")
        # TODO:
        # send generic confirmation email?
        # "You're on a roll!" when they've made multiple?
        # check database?
    else:
        logging.info("Adding User to list.")
        subscribe_user_to_list.apply_async(kwargs={"email": email, "FNAME": FNAME, "LNAME": LNAME})
