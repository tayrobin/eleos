from __future__ import unicode_literals
import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Integration(models.Model):
    """"A service that provides information on the User's daily schedule."""
    name = models.CharField(max_length=200, blank=False)
    description = models.TextField(blank=True, default=None, null=True)
    image_url = models.TextField(blank=True, default=None, null=True)
    auth_url = models.TextField(blank=True, default=None, null=True)
    token_url = models.TextField(blank=True, default=None, null=True)
    users = models.ManyToManyField(User, through='ActiveIntegration', blank=True)

    def __str__(self):
        return self.name


class Payload(models.Model):
    """"What gets delivered to the User in a Moment."""
    name = models.CharField(max_length=200, blank=False)
    description = models.TextField(blank=True, default=None, null=True)
    image_url = models.TextField(blank=True, default=None, null=True)
    length = models.DurationField("The expected length of time, in seconds, Payload will fill.", blank=True, default=None, null=True)
    deliverable = models.TextField(blank=True, default=None, null=True)

    class Meta:
        ordering = ['length']

    def __str__(self):
        return "[%s] %s" % (self.length, self.name)


class Module(models.Model):
    """"A grouping of Integrations that deliver a Payload."""
    name = models.CharField(max_length=200, blank=False)
    description = models.TextField(blank=True, default=None, null=True)
    image_url = models.TextField(blank=True, default=None, null=True)
    intro_message = models.TextField(blank=True, default=None, null=True)
    required_integrations = models.ManyToManyField(Integration, blank=True)
    possible_payloads = models.ManyToManyField(Payload, blank=True)
    users = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.name


class ActiveIntegration(models.Model):
    """An active connection between a User and an Integration that they've authorized."""
    user = models.ForeignKey(User)
    integration = models.ForeignKey(Integration)
    access_token = models.TextField(blank=True, default=None, null=True)
    external_user_id = models.TextField("Unique ID of User in External Service.", blank=True, default=None, null=True)

    def __str__(self):
        return "%s <--> %s" % (self.user.username, self.integration.name)
