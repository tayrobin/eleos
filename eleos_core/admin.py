from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import *

class GiftedMomentAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'fbm_sent_status', 'fbm_read_status')

admin.site.register(Integration)
admin.site.register(Module)
admin.site.register(Payload)
admin.site.register(ActiveIntegration)
admin.site.register(GiftedMoment, GiftedMomentAdmin)