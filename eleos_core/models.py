from __future__ import unicode_literals
import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Integration(models.Model):
    name = models.CharField(max_length=200)
    auth_url = models.CharField(max_length=200, default=None)

    def __str__(self):
        return "%s" % self.name


class UserIntegrationLink(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    integration = models.OneToOneField(Integration, on_delete=models.CASCADE)

    def __str__(self):
        return "%s <--> %s" % (self.user.username, self.integration.name)
