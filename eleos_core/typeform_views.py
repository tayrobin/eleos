import os
import json
import datetime
import logging

import psycopg2
import psycopg2.extras
from celery import shared_task
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

logging.basicConfig(format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)

DB_URL = os.environ["DB_URL"]


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


	# parse data from form
	questions = request_body.get("form_response", {}).get("definition", {}).get("fields", [])
	answers = request_body.get("form_response", {}).get("answers", [])


	# check data exists
	if questions == []:
		logging.warning( "questions is empty." )
	if answers == []:
		logging.warning( "answers is empty." )
	

	# match questions to answers
	for question_obj in questions:

		question_id = question_obj.get("id")
		question_type = question_obj.get("type")
		question = question_obj.get("title")

		logging.info( "Question %s" % question_id )
		try:
			logging.info( "Q: %s" % question )
		except:
			logging.info( "Q: --" )


		# match answer by ID
		answer_obj = next((answer_obj for answer_obj in answers if answer_obj.get("field", {}).get("id") == question_id), None)


		if not answer_obj:
			logging.warning( "No answer found for Question ID: %s" % question_id )


		answer_type = answer_obj.get("type")
		if answer_type == "choice":
			answer = answer_obj.get(answer_type, {}).get("label")
		else:
			answer = answer_obj.get(answer_type, {})


		logging.info( "A: %s" % answer )


		# put answer into moment_data
		# oh god this is horrible
		if "your name" in question:
			moment_data["author_name"] = answer
		
		elif "your email" in question:
			moment_data["author_email"] = answer
		
		elif "Who" in question:
			moment_data["recipient_name"] = answer
		
		elif "email" in question:
			moment_data["recipient_email"] = answer

		elif "live" in question:
			moment_data["recipient_city"] = answer
		
		elif "What kind" in question:
			# turn Moment type choice into date converter
			# always saved as 'time' for 'trigger'
			pass
		
		elif "birthday" in question:
			birthday = datetime.datetime.strptime(answer, '%Y-%m-%d').date()
			birthday_datetime = datetime.datetime(birthday.year, birthday.month, birthday.day, 9, 0, 0)
			# TODO: factor in UTC offset from City into datetime string
			# defaulting to Pacific (UTC-7)
			birthday_datetime_string = str(birthday_datetime) + "-07"
			moment_data["trigger_options"]["time"] = birthday_datetime_string

		elif "send" in question:
			moment_data["content"]["url"] = answer

		else:
			logging.warning( "Not catching for Question ID: %s" % question_id )
			try:
				logging.warning( "Q: %s" % question )
			except:
				logging.warning( "Q: --" )



	logging.info( "moment_data: %s" % moment_data )

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

	logging.info( "Inserted successfully!" )


@csrf_exempt
def receiveTypeformWebhook(request):

	if not request.method == "POST":
		logging.warning( "Not a POST" )
		logging.warning( request )
		return HttpResponse("Not a POST request.")
	else:
		logging.info( "POST: %s" % request )
		request_body = json.loads(request.body)
		logging.info( "POST body: %s" % request_body )

		parseFormData.apply_async(kwargs={"request_body":request_body})

		return HttpResponse('OK')