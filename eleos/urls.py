import eleos_core.views
import eleos_core.messenger_views
from django.contrib import admin
from django.conf.urls import url, include
from eleos_core.forms import LoginForm, SignupForm
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, DeleteView
from django.contrib.auth.forms import UserCreationForm

urlpatterns = [
    # basic
    url(r'^$',                                          TemplateView.as_view(template_name='home.html'), name='home'),

    # test
    #url(r'^test/$',                                     eleos_core.views.showTest, name='test'),

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

    # swarm
    url(r'^foursquare_checkin/$',                       eleos_core.views.foursquareCheckin, name='foursquareCheckin'),
    url(r'^receiveOAuth/$',                             eleos_core.views.receiveOAuth, name='receiveOAuth'),

    # facebook
    url(r'^receive_messenger_webhook/$',                eleos_core.messenger_views.receiveMessengerWebhook, name="receiveMessengerWebhook"),
    url(r'^receive_facebook_oauth/$',                   eleos_core.views.receiveFacebookOAuth, name='receiveFacebookOAuth'),

    # admin stuff
    url(r'^admin/',                                     include(admin.site.urls)),
]
