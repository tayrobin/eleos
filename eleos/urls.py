import eleos_core.views
from django.contrib import admin
from django.conf.urls import url, include
from eleos_core.forms import LoginForm, SignupForm
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm

urlpatterns = [
    url(r'^$',                                          TemplateView.as_view(template_name='home.html'), name='home'),
    url(r'^register/',                                  CreateView.as_view(template_name='register.html', form_class=SignupForm, success_url='/login'), name='register'),
    url(r'^login/$',                                    auth_views.login, {'template_name': 'login.html', 'authentication_form': LoginForm}, name='login'),
    url(r'^accounts/login/$',                           auth_views.login, {'template_name': 'login.html', 'authentication_form': LoginForm}, name='login'),
    url(r'^logout/$',                                   auth_views.logout, {'template_name': 'logged_out.html'}, name='logout'),
    url(r'^core/$',                                     eleos_core.views.index, name='core_index'),
    url(r'^integrations/$',                             eleos_core.views.listIntegrations, name='integrations'),
    url(r'^modules/$',                                  eleos_core.views.listModules, name='modules'),
    url(r'^foursquare_checkin/$',                       eleos_core.views.foursquareCheckin, name='foursquareCheckin'),
    url(r'^sendOAuth/(?P<integrationName>[\w]+)/$',     eleos_core.views.sendOAuth, name='sendOAuth'),
    url(r'^receiveOAuth/$',                             eleos_core.views.receiveOAuth, name='receiveOAuth'),
    url(r'^admin/',                                     include(admin.site.urls)),
]
