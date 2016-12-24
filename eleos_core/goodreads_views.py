import os
import requests
from xml.etree import ElementTree
from django.http import HttpResponse
from rauth.service import OAuth1Service, OAuth1Session
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Integration, ActiveIntegration, OAuthCredentials


def getUsersBooks(activeIntegration):

	new_session = OAuth1Session(
		consumer_key = os.environ['GOODREADS_API_KEY'],
		consumer_secret = os.environ['GOODREADS_CLIENT_SECRET'],
		access_token = activeIntegration.access_token,
		access_token_secret = activeIntegration.access_token_secret,
		)

	try:
		response = new_session.get('https://www.goodreads.com/review/list', params={'v':2, 'id':activeIntegration.external_user_id})
		print response.text
	except:
		print "error getting the user %(user)s's books" % {'user': activeIntegration.user}


def goodreadsUserId(activeIntegration):

	new_session = OAuth1Session(
		consumer_key = os.environ['GOODREADS_API_KEY'],
		consumer_secret = os.environ['GOODREADS_CLIENT_SECRET'],
		access_token = activeIntegration.access_token,
		access_token_secret = activeIntegration.access_token_secret,
		)

	response = new_session.get('https://www.goodreads.com/api/auth_user')
	print response.text
	
	try:
		tree = ElementTree.fromstring(response.text)
		userId = tree.find('user').get('id')
		if not activeIntegration.external_user_id:
			activeIntegration.external_user_id = userId
			activeIntegration.save()

			getUsersBooks(activeIntegration)
	except:
		print "error parsing response tree"


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

	goodreads = OAuth1Service(
		consumer_key=os.environ['GOODREADS_API_KEY'],
		consumer_secret=os.environ['GOODREADS_CLIENT_SECRET'],
		name='goodreads',
		request_token_url='http://www.goodreads.com/oauth/request_token',
		authorize_url='http://www.goodreads.com/oauth/authorize',
		access_token_url='http://www.goodreads.com/oauth/access_token',
		base_url='http://www.goodreads.com/'
		)

	session = goodreads.get_auth_session(oAuthCredential.request_token, oAuthCredential.request_token_secret)

	# these values are what you need to save for subsequent access.
	ACCESS_TOKEN = session.access_token
	ACCESS_TOKEN_SECRET = session.access_token_secret
	print "ACCESS_TOKEN: ", ACCESS_TOKEN
	print "ACCESS_TOKEN_SECRET: ", ACCESS_TOKEN_SECRET

	# Create new activeIntegration
	activeIntegration, new = ActiveIntegration.objects.get_or_create(user=request.user, integration=integration, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)

	# pull history
	if new:
		goodreadsUserId(activeIntegration)

	# send back to integrations
	return redirect('/integrations')