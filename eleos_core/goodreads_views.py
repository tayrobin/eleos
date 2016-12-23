import os
import requests
from django.http import HttpResponse


goodreadsKey = os.environ['GOODREADS_API_KEY']
goodreadsSecret = os.environ['GOODREADS_CLIENT_SECRET']


def receiveGoodreadsOAuth(request):

	print "-- receiving Goodreads OAuth --"

	try:
		print request.GET
	except:
		pass

	try:
		print request.POST
	except:
		pass

	integration = get_object_or_404(Integration, name="Goodreads")

	# exchange code for access_token
	response = requests.get(integration.token_url, params={})
	print "access_token response: ", response.json()

	return HttpResponse(status=200)