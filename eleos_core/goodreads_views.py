import os
import requests
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rauth.service import OAuth1Service, OAuth1Session
from django.contrib.auth.decorators import login_required
from .models import Integration, ActiveIntegration, OAuthCredentials


goodreadsKey = os.environ['GOODREADS_API_KEY']
goodreadsSecret = os.environ['GOODREADS_CLIENT_SECRET']


@login_required()
def receiveGoodreadsOAuth(request):

	print "-- receiving Goodreads OAuth --"

	try:
		print "GET: ", request.GET
		data = dict(request.GET)
		oauth_token = data['oauth_token'][0]
		print "oauth_token: ", oauth_token
	except:
		return redirect('/integrations')

	integration = get_object_or_404(Integration, name="Goodreads")
	oAuthCredential = get_object_or_404(OAuthCredentials, request_token=oauth_token)

	session = goodreads.get_auth_session(oAuthCredential.request_token, oAuthCredential.request_token_secret)

	# these values are what you need to save for subsequent access.
	ACCESS_TOKEN = session.access_token
	ACCESS_TOKEN_SECRET = session.access_token_secret
	print "ACCESS_TOKEN: ", ACCESS_TOKEN
	print "ACCESS_TOKEN_SECRET: ", ACCESS_TOKEN_SECRET

	return HttpResponse(status=200)