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
from .models import Integration, Module, ActiveIntegration, GiftedMoment
from .messenger_views import sendMessenger

@csrf_exempt
def foursquareCheckin(request):

	print request.POST
	dataJson = json.loads(dict(request.POST)['checkin'][0])
	print "dataJson", dataJson

	swarmUserId = dataJson['user']['id']
	venueName = dataJson['venue']['name']

	try:
		print "@%s went to %s" % (swarmUserId, venueName)
	except:
		print "weird characters in venueName"

	facebook = Integration.objects.get(name='Facebook')
	swarm = Integration.objects.get(name='Swarm')

	# get Swarm ActiveIntegration
	try:
		ai_swarm = ActiveIntegration.objects.get(external_user_id=swarmUserId, integration=swarm)
	except:
		print "Unable to find ActiveIntegration for this User."
		return HttpResponse(status=201)

	# get FBM ActiveIntegration
	try:
		ai_facebook = ActiveIntegration.objects.get(user=ai_swarm.user, integration=facebook)
		print "Now have ActiveIntegrations for both Swarm and FBM for %s" % ai_facebook.user
	except:
		print "Looks like %s hasn't given permission for FBM." % ai_swarm.user
		return HttpResponse(status=201)

	giftedMoments = GiftedMoment.objects.filter(recipient=ai_swarm.user)

	# deliver Moment (or generic response)
	if len(giftedMoments) > 0:
		giftedMoment = giftedMoments[0]
		if giftedMoment.payload.deliverable_url:
			deliver = giftedMoment.payload.deliverable_url
		else:
			deliver = giftedMoment.payload.deliverable
		hours, remainder = divmod(giftedMoment.payload.length.seconds, 3600)
		minutes, seconds = divmod(remainder, 60)
		message = '%(creator)s created a %(minutes)s:%(seconds)s minute %(context)s Moment for you:\n"%(endorsement)s"\n%(deliverable)s' % {'creator':giftedMoment.creator, 'minutes':minutes, 'seconds':seconds, 'context':giftedMoment.get_context_display(), 'endorsement':giftedMoment.endorsement, 'deliverable':deliver}
		try:
			sendMessenger(recipientId=ai_facebook.external_user_id, messageText=message)
		except:
			return HttpResponse(status=201)
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
