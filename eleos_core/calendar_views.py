import os
import json
import uuid
import random
import logging
import requests
from celery import shared_task
from django.http import HttpResponse
from .messenger_views import sendMessenger
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import ActiveIntegration, Integration, Module

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)

@shared_task
@csrf_exempt
def refreshAuthToken(access_token):

    logging.info("refreshing auth token")

    refreshUrl = "https://www.googleapis.com/oauth2/v4/token"  # POST

    # get refresh token from server
    integration = get_object_or_404(Integration, name='Calendar')
    ai_gcal = get_object_or_404(
        ActiveIntegration, access_token=access_token)
    refresh_token = ai_gcal.refresh_token

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
        logging.info("new access_token saved!")

        return access_token

    else:
        logging.warning("error refreshing token")
        logging.warning("headers: %s" % response.headers)
        logging.warning("text: %s" % response.text)


@shared_task
def askWatchCalendar(calendar, access_token):

    logging.info("asking for permission to watch calendar")

    response = requests.post("https://www.googleapis.com/calendar/v3/calendars/" + calendar + "/events/watch",
                             headers={'Authorization': 'Bearer ' + access_token,
                                      'Content-Type': 'application/json'},
                             data=json.dumps({'id': str(uuid.uuid4()), 'type': 'web_hook', 'address': 'https://eleos-core.herokuapp.com/receive_gcal/'}))
    logging.info(response)
    watchData = response.json()
    logging.info("watchData: %s" % watchData)

    if response.status_code == 200:

        resource_uri = watchData['resourceUri']
        resource_id = watchData['resourceId']
        resource_uuid = watchData['id']

        return True, resource_uri, resource_id, resource_uuid
    else:
        return False, None, None, None


@shared_task
def stopWatchCalendar(user):

    i = get_object_or_404(Integration, name="Calendar")
    ai_gcal = ActiveIntegration.objects.get(user=user, integration=i)
    if ai_gcal:
        stopUri = "https://www.googleapis.com/calendar/v3/channels/stop"
        response = requests.post(stopUri, headers={'Authorization': 'Bearer ' + ai_gcal.access_token, 'Content-Type': 'application/json'},
                                 data=json.dumps({'resourceId': ai_gcal.resource_id, 'id': ai_gcal.resource_uuid}))
        if response.status_code == 200 or response.status_code == 204:
            try:
                logging.info("STOP response: %s" % response.json())
            except:
                logging.warning("No JSON object in STOP response.")
            return True
        elif response.status_code == 401:
            logging.info("outdated access_token\nCalling refresh method")
            access_token = refreshAuthToken(ai_gcal.access_token)
            stopWatchCalendar(user)
        else:
            logging.info("Error")
            logging.info("Status Code: %s" % response.status_code)
            try:
                errorData = response.json()
                logging.warning("STOP response json: %s" % errorData)
                logging.warning("STOP response headers: %s" % response.headers)
            except:
                pass
            return False
    else:
        logging.warning("No GCal ActiveIntegration found for User: %s" % user)
        return False


@shared_task
def getCalendars(access_token):

    logging.info("Fetching Calendars List for user")

    calendarListUrl = "https://www.googleapis.com/calendar/v3/users/me/calendarList"  # GET

    response = requests.get(calendarListUrl, headers={
                            'Content-Type': 'application/json'}, params={'access_token': access_token})
    if response.status_code == 200:

        responseData = response.json()
        logging.info("response: %s" % responseData)

        for calendar in responseData['items']:

            if 'primary' in calendar and calendar['primary'] == True:

                return calendar['id']

    return None


@shared_task
def getNewEvents(uri, uuid, resource_id, next_page_token_given=None):

    print "Updating Events since last sync"

    integration = get_object_or_404(Integration, name='Calendar')
    ai_gcal = get_object_or_404(
        ActiveIntegration, resource_uuid=uuid)
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
        logging.info("newEvents: %s" % json.dumps(newEvents))

        if 'nextPageToken' in newEvents and newEvents['nextPageToken']:
            next_page_token = newEvents['nextPageToken']
            logging.info(
                "Have a nextPageToken.. re-calling sync calendar method recursively")
            getNewEvents.apply_async(
                args=[uri, uuid, resource_id, next_page_token])

        if 'nextSyncToken' in newEvents:
            next_sync_token = newEvents['nextSyncToken']
            logging.info("next_sync_token: %s" % next_sync_token)
            ai_gcal.next_sync_token = next_sync_token
            ai_gcal.save()
            logging.info("next_sync_token saved.")

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
                logging.info("-- Parsing Event Details --")
                # status .. hoping for 'confirmed'
                try:
                    status = newEvent['status']
                    logging.info('status: %s' % status)
                except:
                    status = None
                # start.dateTime .. timestamp with timezone of start
                try:
                    startDateTime = newEvent['start']['dateTime']
                    logging.info('startDateTime: %s' % startDateTime)
                except:
                    startDateTime = None
                # end.dateTime .. timestamp with timezone of end
                try:
                    endDateTime = newEvent['end']['dateTime']
                    logging.info('endDateTime: %s' % endDateTime)
                except:
                    endDateTime = None
                # kind .. hoping for 'calendar#event'
                try:
                    kind = newEvent['kind']
                    logging.info('kind: %s' % kind)
                except:
                    kind = None
                # summary .. Title of the Event
                try:
                    eventTitle = newEvent['summary']
                    logging.info('eventTitle: %s' % eventTitle)
                except:
                    eventTitle = None
                # description .. description of the Event
                try:
                    description = newEvent['description']
                    logging.info('description: %s' % description)
                except:
                    description = None
                # location .. location of the Event
                try:
                    location = newEvent['location']
                    logging.info('location: %s' % location)
                except:
                    location = None
                # id .. ID of the Event
                try:
                    eventId = newEvent['id']
                    logging.info('eventId: %s' % eventId)
                except:
                    eventId = None
                # htmlLink .. link to the Event
                try:
                    htmlLink = newEvent['htmlLink']
                    logging.info('htmlLink: %s' % htmlLink)
                except:
                    htmlLink = None
                # organizer.displayName .. Name of the Person organizing the
                # Event
                try:
                    organizerDisplayName = newEvent['organizer']['displayName']
                    logging.info('organizerDisplayName: %s' %
                                 organizerDisplayName)
                except:
                    organizerDisplayName = None
                # organizer.self .. Boolean for if I am the person organizing the Event ##
                # None & False are the same
                try:
                    organizerIsSelf = newEvent['organizer']['self']
                    logging.info('organizerIsSelf: %s' % organizerIsSelf)
                except:
                    organizerIsSelf = None
                # organizer.email .. Email of the Person organizing the Event
                try:
                    organizerEmail = newEvent['organizer']['email']
                    logging.info('organizerEmail: %s' % organizerEmail)
                except:
                    organizerEmail = None
                # I don't know what the difference between an Organizer and a Creator is... ### (creator seems to always be me, organizer is who physically started the event)
                # creator.displayName .. Name of the Person creating the Event
                try:
                    creatorDisplayName = newEvent['creator']['displayName']
                    logging.info('creatorDisplayName: %s' % creatorDisplayName)
                except:
                    creatorDisplayName = None
                # creator.self .. Boolean for if I am the person creating the Event ##
                # None & False are the same
                try:
                    creatorIsSelf = newEvent['creator']['self']
                    logging.info('creatorIsSelf: %s' % creatorIsSelf)
                except:
                    creatorIsSelf = None
                # creator.email .. Email of the Person creating the Event
                try:
                    creatorEmail = newEvent['creator']['email']
                    logging.info('creatorEmail: %s' % creatorEmail)
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
                                    logging.info("responseStatus: %s" %
                                                 responseStatus)
                                except:
                                    responseStatus = None
                else:
                    responseStatus = 'accepted'
                # end parsing Event Details

                ##### react to details above #####
                if status == 'confirmed' and responseStatus == 'accepted':
                    newCalendarEventMessage = "I see you've accepted a new Calendar Event!\nTitle: %(event_title)s\nDescription: %(event_description)s\nStart: %(start_time)s\nEnd: %(end_time)s\nLocation: %(event_location)s" % {
                        'event_title': eventTitle, 'event_description': description, 'start_time': startDateTime, 'end_time': endDateTime, 'event_location': location}
                    i = Integration.objects.get(name='Facebook')
                    try:
                        ai_fbm = ActiveIntegration.objects.get(
                            user=ai_gcal.user, integration=i)
                    except:
                        ai_fbm = None
                    if ai_fbm:
                        sendMessenger.apply_async(kwargs={'recipientId': ai_fbm.external_user_id,
                                                          'messageText': newCalendarEventMessage})
                    else:
                        logging.warning(
                            "This User has not enabled the Facebook Messenger Integration.")
                        return
            else:
                logging.warning("More than 1 new Calendar Event received.")
                return
        else:
            logging.warning("no new events")

    elif response.status_code == 401:

        logging.warning("outdated access_token\nCalling refresh method")
        access_token = refreshAuthToken(access_token)
        logging.warning(
            "have new access_token saved...recursively calling getNewEvents")
        getNewEvents.apply_async(
            args=[uri, uuid, resource_id, next_page_token_given])

    else:

        logging.warning(response)
        logging.warning("headers: %s" % response.headers)
        logging.warning("text: %s" % response.text)


@csrf_exempt
@shared_task
def receiveGcal(request):

    logging.info("receiving GCal ping now!")

    headers = request.META
    logging.info("headers: %s" % headers)

    try:
        googleResourceUri = headers['HTTP_X_GOOG_RESOURCE_URI']
        logging.info("googleResourceUri: %s" % googleResourceUri)
        googleResourceState = headers['HTTP_X_GOOG_RESOURCE_STATE']
        logging.info("googleResourceState: %s" % googleResourceState)
        googleResourceId = headers['HTTP_X_GOOG_RESOURCE_ID']
        logging.info("googleResourceId: %s" % googleResourceId)
        googleChannelId = headers['HTTP_X_GOOG_CHANNEL_ID']
        logging.info("googleChannelId: %s" % googleChannelId)
        googleMessageNumber = headers['HTTP_X_GOOG_MESSAGE_NUMBER']
        logging.info("googleMessageNumber: %s" % googleMessageNumber)
    except:
        logging.warning("error parsing Google Resources...")
        googleResourceState = 'fail'

    if googleResourceState == 'sync':
        # getAllEvents(googleResourceUri, googleChannelId, googleResourceId)
        logging.info("sync..passing")

    elif googleResourceState == 'exists':
        getNewEvents.apply_async(
            args=[googleResourceUri, googleChannelId, googleResourceId])

    return HttpResponse("OK")


@login_required()
@shared_task
def receiveCalendarOAuth(request):

    inputs = dict(request.GET)
    logging.info("inputs: %s" % inputs)

    tempCode = inputs['code'][0]

    # send to CODE<-->Auth_Token URL
    integration = get_object_or_404(Integration, name='Calendar')

    response = requests.post(integration.token_url, data={"client_id": os.environ['CALENDAR_CLIENT_ID'],
                                                          "client_secret": os.environ['CALENDAR_CLIENT_SECRET'],
                                                          "code": tempCode,
                                                          "redirect_uri": "https://eleos-core.herokuapp.com/receive_calendar_oauth",
                                                          "grant_type": "authorization_code"})
    logging.info(response.text)
    authData = response.json()
    try:
        refreshToken = authData['refresh_token']
    except:
        refreshToken = None
    tokenType = authData['token_type']
    expiresIn = authData['expires_in']
    accessToken = authData['access_token']

    logging.info("%s %s %s" %
                 (request.user.username, integration.name, accessToken))

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

    logging.info("calling watch calendar method")

    primaryCalendar = getCalendars(accessToken)

    if primaryCalendar:

        success, resource_uri, resource_id, resource_uuid = askWatchCalendar(
            primaryCalendar, accessToken)

        if success:
            activeIntegration.resource_uri = resource_uri
            activeIntegration.resource_id = resource_id
            activeIntegration.resource_uuid = resource_uuid
            activeIntegration.save()
            logging.info("%s is now being watched for %s!" %
                         (primaryCalendar, request.user))
        else:
            return HttpResponse('There seems to have been an error... Please try again.')

    else:
        return HttpResponse('Failed to find the primary calendar for this user...')

    # send back to integrations
    return redirect('/integrations')
