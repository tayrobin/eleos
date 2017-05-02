import os
import json
import datetime
import logging

import psycopg2
import psycopg2.extras
from celery import shared_task
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .slack_views import sendTextToSlack
from .mailchimp_views import handle_user_email

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)

DB_URL = os.environ["DB_URL"]


@shared_task
def newMomentCreated(moment_data):

    # notify Eleos Team in Slack
    slackMessage = "A new Moment has been built through Typeform! Huzzah!\nMeet %(author_name)s, who cares about %(recipient_name)s so much, they want to send a <%(content_url)s|Moment> on %(date)s.\nLet's not let %(author_name)s down." % {
        "author_name": moment_data["author_name"], "recipient_name": moment_data["recipient_name"], "content_url": moment_data["content"]["url"], "date": moment_data["trigger_options"]["time"]}

    sendTextToSlack.apply_async(
        kwargs={"text": slackMessage, "channel": "moment_builder"})

    # trigger mailchimp confirmation to Author
    handle_user_email.apply_async(kwargs={"email": moment_data[
                                  "author_email"], "FNAME": moment_data["author_name"]})


@shared_task
def parseFormData(request_body):

    # to be inserted
    moment_data = {
        "recipient_name": None,
        "recipient_email": None,
        "recipient_phone": None,
        "recipient_city": None,
        "trigger_type": "time",
        "trigger_options": {
            "time": None
        },
        "author_name": None,
        "author_email": None,
        "author_phone": None,
        "content": {
            "url": None
        }
    }

    map_question_title_to_database_column_name = {
        "Who's this <strong>Moment</strong> for?": "recipient_name",
        "Fantastic.  What is {{answer_48822380}}'s email address?": "recipient_email",
        "What is your name?": "author_name",
        "What's your email, {{answer_49550960}}?": "author_email",
        "City:": "recipient_city_name",
        "State:": "recipient_state",
        "Country:": "recipient_country",
        "What kind of<strong> Moment</strong> do you want to build for {{answer_48822380}}?": "moment_type",
        "Okay, when is {{answer_48822380}}'s birthday?": "birthday",
        "Great.  Which upcoming holiday do you want to make a <strong>Moment</strong> for {{answer_48822380}} on?": "holiday_choice",
        "Awesome.  What do you want to call your custom <strong>Holiday Moment</strong>?": "holiday_custom_name",
        "Cool.  Let us know the date of your custom <strong>Holiday Moment</strong>.": "holiday_custom_date",
        "What would you like to send to {{answer_48822380}} in this {{answer_48823537}} <strong>Moment</strong>?": "content_url"
    }

    map_holiday_choice_to_date = {
        # datetime.datetime(year, month, day, hour, minute, second)
        "Star Wars Day (May 4, 2017)": datetime.datetime(2017, 05, 04, 9, 0, 0),
        "Cinco de Mayo (May 5, 2017)": datetime.datetime(2017, 05, 05, 9, 0, 0),
        "Mother's Day (May 14, 2017)": datetime.datetime(2017, 05, 14, 9, 0, 0),
        "Memorial Day (May 29, 2017)": datetime.datetime(2017, 05, 29, 9, 0, 0),
        "Father's Day (June 18, 2017)": datetime.datetime(2017, 06, 18, 9, 0, 0),
        "Independence Day (July 4, 2017)": datetime.datetime(2017, 07, 04, 9, 0, 0)
    }

    # store city, state, country for later matching
    location_dict = {
        "recipient_city_name": None,
        "recipient_state": None,
        "recipient_country": None
    }

    # parse data from form
    questions = request_body.get("form_response", {}).get(
        "definition", {}).get("fields", [])
    answers = request_body.get("form_response", {}).get("answers", [])
    hidden_values = request_body.get("form_response", {}).get("hidden", {})

    # check data exists
    if questions == []:
        logging.warning("questions is empty.")
    if answers == []:
        logging.warning("answers is empty.")

    # match questions to answers
    for question_obj in questions:

        question_id = question_obj.get("id")
        question_type = question_obj.get("type")
        question = question_obj.get("title")

        logging.info("Question %s" % question_id)
        try:
            logging.info("Q: %s" % question)
        except:
            logging.info("Q: --")

        # match answer by ID
        answer_obj = next((answer_obj for answer_obj in answers if answer_obj.get(
            "field", {}).get("id") == question_id), None)

        if not answer_obj:
            logging.warning(
                "No answer found for Question ID: %s" % question_id)
        else:

            answer_type = answer_obj.get("type")
            if answer_type == "choice":
                answer = answer_obj.get(answer_type, {}).get("label")
            else:
                answer = answer_obj.get(answer_type, {})

            logging.info("A: %s" % answer)

            # put answer into moment_data
            answer_key = map_question_title_to_database_column_name.get(
                question)
            if answer_key is None:
                # hardcoding since a few question strings are not matching
                # the mapping dict
                if "send" in question:
                    answer_key = "content_url"
                elif "birthday" in question:
                    answer_key = "birthday"
                elif "email address" in question:
                    answer_key = "recipient_email"
                elif "upcoming holiday" in question:
                    answer_key = "holiday_choice"
                elif "call your custom" in question:
                    answer_key = "holiday_custom_name"

            # second chance
            if answer_key is None:
                logging.warning(
                    "No answer_key found for Question: '%s'." % question)
            else:
                if answer_key in moment_data:
                    moment_data[answer_key] = answer

                elif answer_key == "content_url":
                    moment_data["content"]["url"] = answer

                elif answer_key == "moment_type":
                    # options: ["Birthday", "Holiday", "Next Sunny Day", "Next
                    # Rainy Day"]
                    if answer == "Next Sunny Day" or answer == "Next Rainy Day":
                        # TODO: make real...
                        fake_datetime = datetime.datetime.now() + datetime.timedelta(days=7)
                        fake_datetime_string = str(fake_datetime) + "-07"
                        moment_data["trigger_options"][
                            "time"] = fake_datetime_string
                    elif answer == "Birthday":
                        pass  # actual date caught in next question
                    elif answer == "Holiday":
                        pass  # actual date caught or created in next questions
                    else:
                        logging.warning(
                            "Not accounting for Moment Type: %s" % answer)

                elif answer_key == "birthday" or answer_key == "holiday_custom_date":
                    custom_date = datetime.datetime.strptime(
                        answer, '%Y-%m-%d').date()
                    custom_datetime = datetime.datetime(
                        custom_date.year, custom_date.month, custom_date.day, 9, 0, 0)
                    # TODO: factor in UTC offset from City into datetime string
                    # defaulting to Pacific (UTC-7)
                    custom_datetime_string = str(custom_datetime) + "-07"
                    moment_data["trigger_options"]["time"] = custom_datetime_string

                elif answer_key == "holiday_choice":
                    holiday_datetime = map_holiday_choice_to_date.get(answer)
                    if holiday_datetime is None:
                        logging.warning(
                            "No date set for holiday choice: %s" % answer)
                    else:
                        # TODO: factor in UTC offset from City into datetime string
                        # defaulting to Pacific (UTC-7)
                        holiday_datetime_string = str(holiday_datetime) + "-07"
                        moment_data["trigger_options"][
                            "time"] = holiday_datetime_string

                elif answer_key == "holiday_custom_name":
                    logging.info(
                        "Nothing to do with Custom Holiday Names, but this is '%s'." % answer)

                elif answer_key in ["recipient_city_name", "recipient_state", "recipient_country"]:
                    # store city, state, country for later matching
                    location_dict[answer_key] = answer

                else:
                    logging.warning(
                        "Not catching for Answer Key: %s" % answer_key)
                    logging.warning("Q: %s" % question)


    # match city, state, country
    # TODO: geocode or verify authenticity
    city_state_country = [location_dict.get("recipient_city_name"),
        location_dict.get("recipient_state"),
        location_dict.get("recipient_country")]
    moment_data["recipient_city"] = ", ".join(filter(None, city_state_country))


    # utilize hidden values
    if hidden_values.get("author_prefill") == "True":
        if moment_data["author_name"] is None:
            moment_data["author_name"] = hidden_values.get("author_name")
        if moment_data["author_email"] is None:
            moment_data["author_email"] = hidden_values.get("author_email")
    if hidden_values.get("recipient_prefill") == "True":
        if moment_data["recipient_name"] is None:
            moment_data["recipient_name"] = hidden_values.get("recipient_name")
        if moment_data["recipient_email"] is None:
            moment_data["recipient_email"] = hidden_values.get("recipient_email")


    logging.info("moment_data: %s" % moment_data)

    # trigger success flow
    newMomentCreated.apply_async(kwargs={"moment_data": moment_data}, countdown=30.0)

    # prepare dicts to json for inserting
    moment_data["trigger_options"] = json.dumps(
        moment_data["trigger_options"])
    moment_data["content"] = json.dumps(moment_data["content"])

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    insertStatement = """INSERT INTO moments
	(recipient_name, recipient_email, recipient_phone, recipient_city, trigger_type, trigger_options, author_name, author_email, author_phone, content, created_at, updated_at)
	VALUES
	(%(recipient_name)s, %(recipient_email)s, %(recipient_phone)s, %(recipient_city)s, %(trigger_type)s, %(trigger_options)s, %(author_name)s, %(author_email)s, %(author_phone)s, %(content)s, now(), now())"""

    cur.execute(insertStatement, moment_data)
    conn.commit()

    logging.info("Inserted successfully!")


@csrf_exempt
def receiveTypeformWebhook(request):

    if request.method != "POST":
        logging.warning("Not a POST")
        logging.warning(request)
        return HttpResponse("Not a POST request.")
    else:
        logging.info("POST: %s" % request)
        request_body = json.loads(request.body)
        # logging.info("POST body: %s" % request_body)

        parseFormData.apply_async(kwargs={"request_body": request_body})

        return HttpResponse('OK')
