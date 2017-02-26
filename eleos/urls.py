import eleos_core.views
import eleos_core.calendar_views
import eleos_core.messenger_views
import eleos_core.goodreads_views
import eleos_core.foursquare_views
import eleos_core.moment_views
from django.contrib import admin
from django.conf.urls import url, include
from eleos_core.forms import LoginForm, SignupForm, MomentForm
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, DeleteView
from django.contrib.auth.forms import UserCreationForm

urlpatterns = [
    # basic
    url(r'^$',                                          TemplateView.as_view(template_name='home.html'), name='home'),

    # register/login/logout
    url(r'^register/',                                  CreateView.as_view(template_name='register.html', form_class=SignupForm, success_url='/login'), name='register'),
    url(r'^login/$',                                    auth_views.login, {'template_name': 'login.html', 'authentication_form': LoginForm}, name='login'),
    url(r'^accounts/login/$',                           auth_views.login, {'template_name': 'login.html', 'authentication_form': LoginForm}, name='login'),
    url(r'^logout/$',                                   auth_views.logout, {'template_name': 'logged_out.html'}, name='logout'),

    # standard site pages
    url(r'^integrations/$',                             eleos_core.views.listIntegrations, name='integrations'),
    url(r'^modules/$',                                  eleos_core.views.listModules, name='modules'),

    # module management
    url(r'^activate_module/(?P<id>\d+)/$',              eleos_core.views.activateModule, name="activateModule"),
    url(r'^deactivate_module/(?P<id>\d+)/$',            eleos_core.views.deactivateModule, name="deactivateModule"),

    # integration management
    url(r'^delete_active_integration/(?P<name>\w+)/$',  eleos_core.views.deleteActiveIntegration, name="deleteActiveIntegration"),
    url(r'^sendOAuth/(?P<integrationName>[\w]+)/$',     eleos_core.views.sendOAuth, name='sendOAuth'),

    # GiftedMoment management
    url(r'^deliver_gifted_moment/(?P<id>\d+)/$',        eleos_core.views.deliverGiftedMoment, name='deliverGiftedMoment'),

    # foursquare/swarm
    url(r'^foursquare_checkin/$',                       eleos_core.foursquare_views.foursquareCheckin, name='foursquareCheckin'),
    url(r'^receiveOAuth/$',                             eleos_core.foursquare_views.receiveFoursquareOAuth, name='receiveOAuth'),

    # facebook
    url(r'^receive_messenger_webhook/$',                eleos_core.messenger_views.receiveMessengerWebhook, name="receiveMessengerWebhook"),
    url(r'^receive_facebook_oauth/$',                   eleos_core.messenger_views.receiveFacebookOAuth, name='receiveFacebookOAuth'),

    # google calendar
    url(r'^receive_gcal/$',                             eleos_core.calendar_views.receiveGcal, name='receiveGcal'),
    url(r'^receive_calendar_oauth/$',                   eleos_core.calendar_views.receiveCalendarOAuth, name='receiveCalendarOAuth'),

    # goodreads
    url(r'^receive_goodreads_oauth/$',                  eleos_core.goodreads_views.receiveGoodreadsOAuth, name='receiveGoodreadsOAuth'),

    # slack
    url(r'^receive_slack_webhook/$',                    eleos_core.slack_views.receiveSlackWebhook, name='receiveSlackWebhook'),

    # admin stuff
    url(r'^admin/',                                     include(admin.site.urls)),

    # moments
    url(r'^moment/new',                                 CreateView.as_view(template_name='create_moment.html', form_class=MomentForm, success_url='/'), name='new_moment'),
    url(r'^moment/post',                                eleos_core.moment_views.createNewMoment, name='post_moment_form'),
]
