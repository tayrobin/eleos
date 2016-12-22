import os
import json
import uuid
import random
import requests
#import httplib2
from django.http import HttpResponse
from .messenger_views import sendMessenger
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ActiveIntegration, Integration, Module


@csrf_exempt
def refreshAuthToken(access_token):

    print "refreshing auth token"

    refreshUrl = "https://www.googleapis.com/oauth2/v4/token"  # POST

    # get refresh token from server
    integration = get_object_or_404(Integration, name='Calendar')
    ai_gcal = ActiveIntegration.get_object_or_404(
        integration=integration, access_token=access_token)
    refresh_token = ai_gcal.refresh_token

    '''
	else:
		print "error retrieving refresh_token from server for access_token: %s"%access_token
		print "need the user to re-auth calendar access"
		## really I should be using a specific param to ask for new refresh_token as well..
		## set prompt=consent in the offline access step (https://developers.google.com/identity/protocols/OAuth2WebServer#refresh)
		return render('google-auth.html')
	'''

    response = requests.post(refreshUrl, data={'client_id': os.environ['CALENDAR_CLIENT_ID'], 'client_secret': os.environ[
                             'CALENDAR_CLIENT_SECRET'], 'refresh_token': refresh_token, 'grant_type': 'refresh_token'})
    if response.status_code == 200:
        newData = response.json()
        access_token = newData['access_token']
        expires_in = newData['expires_in']
        token_type = newData['token_type']

        # now update server
        ai_gcal.access_token = access_token
        ai_gcal.expires_in = expires_in
        ai_gcal.token_type = token_type
        ai_gcal.save()
        print "new access_token saved!"

        return access_token

    else:
        print "error refreshing token"
        print "headers: ", response.headers
        print "text: ", response.text


def askWatchCalendar(calendar, access_token):

    print "asking for permission to watch calendar"

    response = requests.post("https://www.googleapis.com/calendar/v3/calendars/" + calendar + "/events/watch",
                             headers={'Authorization': 'Bearer ' + access_token,
                                      'Content-Type': 'application/json'},
                             data=json.dumps({'id': str(uuid.uuid4()), 'type': 'web_hook', 'address': 'https://eleos-core.herokuapp.com/receive_gcal/'}))
    print response
    watchData = response.json()
    print "watchData: ", watchData

    if response.status_code == 200:

        resource_uri = watchData['resourceUri']
        resource_id = watchData['resourceId']
        resource_uuid = watchData['id']

        return True, resource_uri, resource_id, resource_uuid
    else:
        return False, None, None, None


def getCalendars(access_token):

    print "Fetching Calendars List for user"

    calendarListUrl = "https://www.googleapis.com/calendar/v3/users/me/calendarList"  # GET

    response = requests.get(calendarListUrl, headers={
                            'Content-Type': 'application/json'}, params={'access_token': access_token})
    if response.status_code == 200:

        responseData = response.json()
        print "response: ", responseData

        for calendar in responseData['items']:

            if 'primary' in calendar and calendar['primary'] == True:

                return calendar['id']

    return None


def getEvent(event_id, uri, access_token):

    print "Fetching Calendar Event for user"

    # seemingly producing a 404 error, need to read Docs more...
    eventUrl = uri.strip('?maxResults=250&alt=json') + "/" + event_id

    response = requests.get(eventUrl, headers={
                            'Content-Type': 'application/json'}, params={'access_token': access_token})

    if response.status_code == 200:
        eventDetails = response.json()
        print "eventDetails: ", eventDetails
    else:
        print response
        print "headers: ", response.headers
        print "text: ", response.text


def getAllEvents(uri, uuid, resource_id):

    print "Fetching all Calendar Events for user"

    cur.execute(getAccessToken, {'resource_uri': uri,
                                 'resource_uuid': uuid, 'resource_id': resource_id})
    access_token = cur.fetchone()[0]

    response = requests.get(uri, headers={'Content-Type': 'application/json'}, params={
                            'access_token': access_token, 'maxResults': 10})

    if response.status_code == 200:
        responseData = response.json()
        print "response: ", responseData

        next_sync_token = responseData['nextSyncToken']
        print "next_sync_token: ", next_sync_token

        cur.execute(saveNextSyncToken, {'next_sync_token': next_sync_token,
                                        'resource_uri': uri, 'resource_uuid': uuid, 'resource_id': resource_id})
        conn.commit()
        print "next_sync_token saved."


def getNewEvents(uri, uuid, resource_id, next_page_token_given=None):

    print "Updating Events since last sync"

    integration = get_object_or_404(Integration, name='Calendar')
    ai_gcal = ActiveIntegration.get_object_or_404(
        integration=integration, resource_uuid=uuid)
    access_token = ai_gcal.access_token
    sync_token = ai_gcal.next_sync_token

    if next_page_token_given:
        response = requests.get(uri, headers={'Content-Type': 'application/json'}, params={
                                'access_token': access_token, 'syncToken': sync_token, 'pageToken': next_page_token_given})
    else:
        response = requests.get(uri, headers={'Content-Type': 'application/json'}, params={
                                'access_token': access_token, 'syncToken': sync_token})

    if response.status_code == 200:

        newEvents = response.json()
        print "newEvents: ", json.dumps(newEvents)

        if 'nextPageToken' in newEvents and newEvents['nextPageToken']:
            next_page_token = newEvents['nextPageToken']
            print "Have a nextPageToken.. re-calling sync calendar method recursively"
            getNewEvents(uri, uuid, resource_id, next_page_token)

        if 'nextSyncToken' in newEvents:
            next_sync_token = newEvents['nextSyncToken']
            print "next_sync_token: ", next_sync_token
            ai_gcal.next_sync_token = next_sync_token
            ai_gcal.save()
            print "next_sync_token saved."

        if 'items' in newEvents and newEvents['items']:
            if len(newEvents['items']) == 1:

                newEvent = newEvents['items'][0]

                #### Event Details Overview ####
                # cancelled Event
                # status: cancelled
                # kind: calendar#event
                # eventId: 6tfas1pil9m79d9v1d1gotb0eo
                # self-created Event
                # status: confirmed
                # startDateTime: 2016-10-11T17:30:00-07:00
                # endDateTime: 2016-10-11T18:30:00-07:00
                # kind: calendar#event
                # eventTitle: fun stuff 3
                # eventId: hnec4hn7ept4p78i0k18qabei0
                # htmlLink: https://www.google.com/calendar/event?eid=aG5lYzRobjdlcHQ0cDc4aTBrMThxYWJlaTAgdGF5bG9yQGFwcGJhY2tyLmNvbQ
                # organizerDisplayName: Taylor Robinson
                # organizerIsSelf: True
                # organizerEmail: taylor@appbackr.com
                # creatorDisplayName: Taylor Robinson
                # creatorIsSelf: True
                # creatorEmail: taylor@appbackr.com
                # invited to someone else's Event
                # status: confirmed
                # startDateTime: 2016-10-11T19:00:00-07:00
                # endDateTime: 2016-10-11T20:00:00-07:00
                # kind: calendar#event
                # eventTitle: Breakfast at Tiffany's
                # eventId: 932hp9b1dqt2c4rf20djt8e3g0
                # htmlLink: https://www.google.com/calendar/event?eid=OTMyaHA5YjFkcXQyYzRyZjIwZGp0OGUzZzAgdGF5bG9yQGFwcGJhY2tyLmNvbQ
                # organizerDisplayName: Taylor Robinson
                # organizerEmail: taylor.howard.robinson@gmail.com
                # creatorDisplayName: Taylor Robinson
                # creatorIsSelf: True
                # creatorEmail: taylor@appbackr.com

                # also have attendee objects list
                # responseStatus: needsAction, accepted, declined
                # self: True
                # email:
                # displayName:
                # organizer: True

                # parse Event Details
                print "-- Parsing Event Details --"
                # status .. hoping for 'confirmed'
                try:
                    status = newEvent['status']
                    print 'status:', status
                except:
                    status = None
                # start.dateTime .. timestamp with timezone of start
                try:
                    startDateTime = newEvent['start']['dateTime']
                    print 'startDateTime:', startDateTime
                except:
                    startDateTime = None
                # end.dateTime .. timestamp with timezone of end
                try:
                    endDateTime = newEvent['end']['dateTime']
                    print 'endDateTime:', endDateTime
                except:
                    endDateTime = None
                # kind .. hoping for 'calendar#event'
                try:
                    kind = newEvent['kind']
                    print 'kind:', kind
                except:
                    kind = None
                # summary .. Title of the Event
                try:
                    eventTitle = newEvent['summary']
                    print 'eventTitle:', eventTitle
                except:
                    eventTitle = None
                # description .. description of the Event
                try:
                    description = newEvent['description']
                    print 'description:', description
                except:
                    description = None
                # location .. location of the Event
                try:
                    location = newEvent['location']
                    print 'location:', location
                except:
                    location = None
                # id .. ID of the Event
                try:
                    eventId = newEvent['id']
                    print 'eventId:', eventId
                except:
                    eventId = None
                # htmlLink .. link to the Event
                try:
                    htmlLink = newEvent['htmlLink']
                    print 'htmlLink:', htmlLink
                except:
                    htmlLink = None
                # organizer.displayName .. Name of the Person organizing the
                # Event
                try:
                    organizerDisplayName = newEvent['organizer']['displayName']
                    print 'organizerDisplayName:', organizerDisplayName
                except:
                    organizerDisplayName = None
                # organizer.self .. Boolean for if I am the person organizing the Event ##
                # None & False are the same
                try:
                    organizerIsSelf = newEvent['organizer']['self']
                    print 'organizerIsSelf:', organizerIsSelf
                except:
                    organizerIsSelf = None
                # organizer.email .. Email of the Person organizing the Event
                try:
                    organizerEmail = newEvent['organizer']['email']
                    print 'organizerEmail:', organizerEmail
                except:
                    organizerEmail = None
                # I don't know what the difference between an Organizer and a Creator is... ### (creator seems to always be me, organizer is who physically started the event)
                # creator.displayName .. Name of the Person creating the Event
                try:
                    creatorDisplayName = newEvent['creator']['displayName']
                    print 'creatorDisplayName:', creatorDisplayName
                except:
                    creatorDisplayName = None
                # creator.self .. Boolean for if I am the person creating the Event ##
                # None & False are the same
                try:
                    creatorIsSelf = newEvent['creator']['self']
                    print 'creatorIsSelf:', creatorIsSelf
                except:
                    creatorIsSelf = None
                # creator.email .. Email of the Person creating the Event
                try:
                    creatorEmail = newEvent['creator']['email']
                    print 'creatorEmail:', creatorEmail
                except:
                    creatorEmail = None
                if 'attendees' in newEvent:
                    for person in newEvent['attendees']:
                        if 'self' in person:
                            if person['self']:
                                # responseStatus ... needsAction, accepted,
                                # declined
                                try:
                                    responseStatus = person['responseStatus']
                                    print "responseStatus:", responseStatus
                                except:
                                    responseStatus = None
                else:
                    responseStatus = 'accepted'
                # end parsing Event Details

                ##### react to details above #####
                if status == 'confirmed' and responseStatus == 'accepted':

                    # ping in FBM
                    newCalendarEventMessage = "I see you've accepted a new Calendar Event!\nTitle: %(event_title)s\nDescription: %(event_description)s\nStart: %(start_time)s\nEnd: %(end_time)s\nLocation: %(event_location)s" % {
                        'event_title': eventTitle, 'event_description': description, 'start_time': startDateTime, 'end_time': endDateTime, 'event_location': location}
                i = Integration.objects.get(name='Facebook')
                ai_fbm = ActiveIntegration.get_object_or_404(
                    user=ai_gcal.user, integration=i)
                if ai.external_user_id:
                    sendMessenger(recipientId=ai_fbm.external_user_id,
                                  messageText=newCalendarEventMessage)
                else:
                    print "This User has not enabled the Facebook Messenger Integration."
                    return
            else:
                print "More than 1 new Calendar Event received."
                return
        else:
            print "no new events"

    elif response.status_code == 401:

        print "outdated access_token\nCalling refresh method"
        access_token = refreshAuthToken(access_token)
        print "have new access_token saved...recursively calling getNewEvents"
        getNewEvents(uri, uuid, resource_id, next_page_token_given)

    else:

        print response
        print "headers: ", response.headers
        print "text: ", response.text


@csrf_exempt
def receiveGcal(request):

    print "receiving GCal ping now!"

    headers = request.META
    print "headers: ", headers

    try:
        googleResourceUri = headers['HTTP_X_GOOG_RESOURCE_URI']
        print "googleResourceUri: ", googleResourceUri
        googleResourceState = headers['HTTP_X_GOOG_RESOURCE_STATE']
        print "googleResourceState: ", googleResourceState
        googleResourceId = headers['HTTP_X_GOOG_RESOURCE_ID']
        print "googleResourceId: ", googleResourceId
        googleChannelId = headers['HTTP_X_GOOG_CHANNEL_ID']
        print "googleChannelId: ", googleChannelId
        googleMessageNumber = headers['HTTP_X_GOOG_MESSAGE_NUMBER']
        print "googleMessageNumber: ", googleMessageNumber
    except:
        print "error parsing Google Resources..."
        googleResourceState = 'fail'

    if googleResourceState == 'sync':
        # getAllEvents(googleResourceUri, googleChannelId, googleResourceId)
        print "sync..passing"

    elif googleResourceState == 'exists':
        getNewEvents(googleResourceUri, googleChannelId, googleResourceId)

    return HttpResponse("OK")


@login_required()
def receiveCalendarOAuth(request):

    inputs = dict(request.GET)
    print "inputs: ", inputs

    tempCode = inputs['code'][0]

    # send to CODE<-->Auth_Token URL
    integration = get_object_or_404(Integration, name='Calendar')

    response = requests.post(integration.token_url, data={"client_id": os.environ['CALENDAR_CLIENT_ID'],
                                                          "client_secret": os.environ['CALENDAR_CLIENT_SECRET'],
                                                          "code": tempCode,
                                                          "redirect_uri": "https://eleos-core.herokuapp.com/receive_calendar_oauth",
                                                          "grant_type": "authorization_code"})
    print response.text
    authData = response.json()
    try:
        refreshToken = authData['refresh_token']
    except:
        refreshToken = None
    tokenType = authData['token_type']
    expiresIn = authData['expires_in']
    accessToken = authData['access_token']

    print request.user.username, integration.name, accessToken

    # Create new Link
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=request.user, integration=integration)

    # add optional details
    if not activeIntegration.access_token:
        activeIntegration.access_token = accessToken
        activeIntegration.save()
    if not activeIntegration.refresh_token and refreshToken:
        activeIntegration.refresh_token = refreshToken
        activeIntegration.save()
    if not activeIntegration.token_type and tokenType:
        activeIntegration.token_type = tokenType
        activeIntegration.save()
    if not activeIntegration.expires_in and expiresIn:
        activeIntegration.expires_in = expiresIn
        activeIntegration.save()

    print "calling watch calendar method"

    primaryCalendar = getCalendars(accessToken)

    if primaryCalendar:

        success, resource_uri, resource_id, resource_uuid = askWatchCalendar(
            primaryCalendar, accessToken)

        if success:
            activeIntegration.resource_uri = resource_uri
            activeIntegration.resource_id = resource_id
            activeIntegration.resource_uuid = resource_uuid
            activeIntegration.save()
            print "%s is now being watched for %s!" % (primaryCalendar, request.user)
        else:
            return HttpResponse('There seems to have been an error... Please try again.')

    else:
        return HttpResponse('Failed to find the primary calendar for this user...')

    # send back to integrations
    return redirect('/integrations')
