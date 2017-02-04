from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import *


class GiftedMomentAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'creator', 'recipient', 'fbm_sent_status', 'fbm_read_status', 'fbm_payload_click_status', 'fbm_payload_click_count')


class MomentAdmin(admin.ModelAdmin):
	list_display = ('__unicode__', 'user', 'trigger', 'created_at', 'updated_at')


admin.site.register(Module)
admin.site.register(Payload)
admin.site.register(Integration)
admin.site.register(ActiveIntegration)
admin.site.register(Moment, MomentAdmin)
admin.site.register(GiftedMoment, GiftedMomentAdmin)