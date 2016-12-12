from django.conf.urls import url
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^integrations/$', views.listUserIntegrations, name='integrations'),
    url(r'^login/$', auth_views.login, {'template_name': 'login.html'}, name='login'),
]
