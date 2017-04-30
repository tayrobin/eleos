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
		"author_name": moment_data["author_name"], "recipient_name": moment_data["recipient_name"], "content_url":moment_data["content"]["url"], "date": moment_data["trigger_options"]["time"]}

	sendTextToSlack.apply_async(
		kwargs={"text": slackMessage, "channel": "moment_builder"})


	# trigger mailchimp confirmation to Author
	#handle_user_email.apply_async(kwargs={"email": moment_data["author_email"], "FNAME": moment_data["author_name"]})
	handle_user_email(email=moment_data["author_email"], FNAME=moment_data["author_name"])


@shared_task
def parseFormData(request_body):

	# to be inserted
	moment_data = {
		"recipient_name": "",
		"recipient_email": "",
		"recipient_phone": None,
		"recipient_city": "",
		"trigger_type": "time",
		"trigger_options": {
			"time": ""
		},
		"author_name": "",
		"author_email": "",
		"author_phone": None,
		"content": {
			"url": ""
		}
	}

	map_question_title_to_database_column_name = {
		"What is your name?": "author_name",
		"What's your email, {{answer_49550960}}?": "author_email",
		"Who's this <strong>Moment</strong> for?": "recipient_name",
		"Fantastic.  What is {{answer_48822380}}'s email address?": "recipient_email",
		"Great, and where does {{answer_48822380}} live?": "recipient_city",
		"What kind of<strong> Moment</strong> do you want to build for {{answer_48822380}}?": "moment_type",
		"Okay, when is {{answer_48822380}}'s birthday?": "birthday",
		"What would you like to send to {{answer_48822380}} in this {{answer_48823537}} <strong>Moment</strong>?": "content_url"
	}

	# parse data from form
	questions = request_body.get("form_response", {}).get(
		"definition", {}).get("fields", [])
	answers = request_body.get("form_response", {}).get("answers", [])

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
				# hardcoding since a few question strings are not matching the mapping dict
				if "send" in question:
					answer_key = "content_url"
				elif "birthday" in question:
					answer_key = "birthday"
				elif "email address" in question:
					answer_key = "recipient_email"
				elif "live" in question:
					answer_key = "recipient_city"

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
					pass  # not factoring in for now
				elif answer_key == "birthday":
					birthday = datetime.datetime.strptime(
						answer, '%Y-%m-%d').date()
					birthday_datetime = datetime.datetime(
						birthday.year, birthday.month, birthday.day, 9, 0, 0)
					# TODO: factor in UTC offset from City into datetime string
					# defaulting to Pacific (UTC-7)
					birthday_datetime_string = str(birthday_datetime) + "-07"
					moment_data["trigger_options"]["time"] = birthday_datetime_string
				else:
					logging.warning(
						"Not catching for Question ID: %s" % question_id)
					logging.warning("Q: %s" % question)

	logging.info("moment_data: %s" % moment_data)

	# trigger success flow
	newMomentCreated.apply_async(kwargs={"moment_data": moment_data})

	# prepare dicts to json for inserting
	moment_data["trigger_options"] = json.dumps(moment_data["trigger_options"])
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
