import os
import requests
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Integration, ActiveIntegration
from rauth.service import OAuth1Service, OAuth1Session
from django.contrib.auth.decorators import login_required


goodreadsKey = os.environ['GOODREADS_API_KEY']
goodreadsSecret = os.environ['GOODREADS_CLIENT_SECRET']


@login_required()
def receiveGoodreadsOAuth(request):

	print "-- receiving Goodreads OAuth --"

	try:
		print "GET: ", request.GET
		data = dict(request.GET)
		oauth_token = data['oauth_token']
	except:
		pass

	integration = get_object_or_404(Integration, name="Goodreads")

	# exchange code for access_token
	response = requests.get(integration.token_url, params={'oauth_token': oauth_token})
	try:
		print "access_token response: ", response.json()
	except:
		print "access_token response text: ", response.text

	'''
	goodreads = OAuth1Service(
		consumer_key=os.environ['GOODREADS_API_KEY'],
        consumer_secret=os.environ['GOODREADS_CLIENT_SECRET'],
		name='goodreads',
		request_token_url='http://www.goodreads.com/oauth/request_token',
		authorize_url='http://www.goodreads.com/oauth/authorize',
		access_token_url='http://www.goodreads.com/oauth/access_token',
		base_url='http://www.goodreads.com/'
		)

	# head_auth=True is important here; this doesn't work with oauth2 for some reason
	request_token, request_token_secret = goodreads.get_request_token(header_auth=True)

	session = goodreads.get_auth_session(request_token, request_token_secret)

	# these values are what you need to save for subsequent access.
	ACCESS_TOKEN = session.access_token
	ACCESS_TOKEN_SECRET = session.access_token_secret
	'''

	return HttpResponse(status=200)