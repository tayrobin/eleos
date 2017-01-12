import os
import logging
import requests
from celery import shared_task
from xml.etree import ElementTree
from django.http import HttpResponse
from rauth.service import OAuth1Service, OAuth1Session
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Integration, ActiveIntegration, OAuthCredentials

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)


@shared_task
def getUsersBooks(activeIntegration):

    new_session = OAuth1Session(
        consumer_key=os.environ['GOODREADS_API_KEY'],
        consumer_secret=os.environ['GOODREADS_CLIENT_SECRET'],
        access_token=activeIntegration.access_token,
        access_token_secret=activeIntegration.access_token_secret,
    )

    try:
        response = requests.get('https://www.goodreads.com/review/list/' +
                                activeIntegration.external_user_id + '.xml?v=2' + '&key=' + os.environ['GOODREADS_API_KEY'])
        logging.info("%(user)s's Books:" % {'user': activeIntegration.user})
        logging.info(response.text)
    except:
        logging.warning("error getting the user %(user)s's books" %
                        {'user': activeIntegration.user})


@shared_task
def goodreadsUserId(activeIntegration):

    new_session = OAuth1Session(
        consumer_key=os.environ['GOODREADS_API_KEY'],
        consumer_secret=os.environ['GOODREADS_CLIENT_SECRET'],
        access_token=activeIntegration.access_token,
        access_token_secret=activeIntegration.access_token_secret,
    )

    response = new_session.get('https://www.goodreads.com/api/auth_user')

    try:
        tree = ElementTree.fromstring(response.text)
        userId = tree.find('user').get('id')
        logging.info("%(user)s's Goodreads userId: %(userId)s" %
                     {'user': activeIntegration.user, 'userId': userId})
        if not activeIntegration.external_user_id:
            activeIntegration.external_user_id = userId
            activeIntegration.save()

            getUsersBooks.apply_async(args=[activeIntegration])
    except:
        logging.warning("error parsing response userId tree")
        logging.warning(response.text)


@login_required()
@shared_task
def receiveGoodreadsOAuth(request):

    logging.info("-- receiving Goodreads OAuth --")

    try:
        logging.info("GET: %s" % request.GET)
        data = dict(request.GET)
        oauth_token = data['oauth_token'][0]
        logging.info("oauth_token: %s" % oauth_token)
    except:
        return redirect('/integrations')

    integration = get_object_or_404(Integration, name="Goodreads")
    oAuthCredential = get_object_or_404(
        OAuthCredentials, request_token=oauth_token)

    goodreads = OAuth1Service(
        consumer_key=os.environ['GOODREADS_API_KEY'],
        consumer_secret=os.environ['GOODREADS_CLIENT_SECRET'],
        name='goodreads',
        request_token_url='http://www.goodreads.com/oauth/request_token',
        authorize_url='http://www.goodreads.com/oauth/authorize',
        access_token_url='http://www.goodreads.com/oauth/access_token',
        base_url='http://www.goodreads.com/'
    )

    session = goodreads.get_auth_session(
        oAuthCredential.request_token, oAuthCredential.request_token_secret)

    # these values are what you need to save for subsequent access.
    ACCESS_TOKEN = session.access_token
    ACCESS_TOKEN_SECRET = session.access_token_secret
    logging.info("ACCESS_TOKEN: %s" % ACCESS_TOKEN)
    logging.info("ACCESS_TOKEN_SECRET: %s" % ACCESS_TOKEN_SECRET)

    # Create new activeIntegration
    activeIntegration, new = ActiveIntegration.objects.get_or_create(
        user=request.user, integration=integration, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)

    # pull history
    if new:
        goodreadsUserId.apply_async(args=[activeIntegration])

    # send back to integrations
    return redirect('/integrations')
