import os
import json
import requests
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Integration, Module, ActiveIntegration
from .messenger_views import sendMessenger

@csrf_exempt
def foursquareCheckin(request):

	print request.POST
	dataJson = json.loads(dict(request.POST)['checkin'][0])
	print "dataJson", dataJson

	swarmUserId = dataJson['user']['id']
	venueName = dataJson['venue']['name']

	print "@%s went to %s" % (swarmUserId, venueName)

	facebook = Integration.objects.get(name='Facebook')
	swarm = Integration.objects.get(name='Swarm')

	try:
		ai_swarm = ActiveIntegration.objects.get(external_user_id=swarmUserId, integration=swarm)
	except:
		print "Unable to find ActiveIntegration for this User."
		return HttpResponse(status=201)

	try:
		ai_facebook = ActiveIntegration.objects.get(user=ai_swarm.user, integration=facebook)
		print "Now have ActiveIntegrations for both Swarm and FBM for %s" % ai_facebook.user
	except:
		print "Looks like %s hasn't given permission for FBM." % ai_swarm.user
		return HttpResponse(status=201)

	# send intro message
	if False:
		pass
	else:
		try:
			sendMessenger(recipientId=ai_facebook.external_user_id, messageText="Nice checkin at %s!"%venueName)
		except:
			return HttpResponse(status=201)

	return HttpResponse(status=201)


def foursquareDetails(activeIntegration):

	# get user profile
	response = requests.get('https://api.foursquare.com/v2/users/self', {'oauth_token':activeIntegration.access_token, 'v':'20161212'})
	data = response.json()
	print activeIntegration.user.username, "User Profile", data

	try:
		user_id = data['response']['user']['id']
		activeIntegration.external_user_id = user_id
		activeIntegration.save()
	except:
		print "Unable to parse User ID from response."

	# get checkin history
	response = requests.get('https://api.foursquare.com/v2/users/self/checkins', {'oauth_token':activeIntegration.access_token, 'v':'20161212'})
	data = response.json()
	print activeIntegration.user.username, "Checkin History", data


@login_required()
def receiveFoursquareOAuth(request):

	# parse CODE
	tempCode = request.GET['code']

	# send to CODE<-->Auth_Token URL
	if True:
		integration = get_object_or_404(Integration, name='Swarm')

		response = requests.get(integration.token_url, {"client_id":os.environ['FOURSQUARE_CLIENT_ID'],
														"client_secret":os.environ['FOURSQUARE_CLIENT_SECRET'],
														"grant_type":"authorization_code", "code":tempCode,
														"redirect_uri":"https://eleos-core.herokuapp.com/receiveOAuth"})

		response = response.json()
		access_token = response['access_token']
		print request.user.username, integration.name, access_token

	# Create new Link
	activeIntegration, new = ActiveIntegration.objects.get_or_create(user=request.user, integration=integration, access_token=access_token)

	# pull history
	if new and integration.name=='Swarm':
		foursquareDetails(activeIntegration)

	# send back to integrations
	return redirect('/integrations')
