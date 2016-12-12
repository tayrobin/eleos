from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import *

# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class UserIntegrationLinkInline(admin.StackedInline):
    model = UserIntegrationLink
    can_delete = False
    verbose_name_plural = 'User Integration Link'

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserIntegrationLinkInline, )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Integration)
admin.site.register(UserIntegrationLink)
admin.site.register(Module)
admin.site.register(Payload)
