from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView
import eleos_core.views
from eleos_core.forms import LoginForm

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='home.html'), name='home'),
    url(r'^login/$', auth_views.login, {'template_name': 'login.html', 'authentication_form': LoginForm}, name='login'),
    url(r'^logout/$', auth_views.logout, {'template_name': 'logged_out.html'}, name='logout'),
    url(r'^core/$', eleos_core.views.index, name='core_index'),
    url(r'^integrations/$', eleos_core.views.listUserIntegrations, name='integrations'),
    url(r'^admin/', admin.site.urls),
]
