from __future__ import unicode_literals
import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Integration(models.Model):
    """"A service that provides information on the User's daily schedule."""
    name = models.CharField(max_length=200, null=False)
    description = models.TextField(null=True)
    image_url = models.TextField(null=True)
    auth_url = models.TextField(null=True)
    token_url = models.TextField(null=True)
    users = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.name


class Payload(models.Model):
    """"What gets delivered to the User in a Moment."""
    name = models.CharField(max_length=200, null=False)
    description = models.TextField(null=True)
    image_url = models.TextField(null=True)
    length = models.DurationField("The expected length of time Payload will fill.", null=True)
    deliverable = models.TextField(null=True)

    class Meta:
        ordering = ['length']

    def __str__(self):
        return "[%s] %s" % (self.length, self.name)


class Module(models.Model):
    """"A grouping of Integrations that deliver a Payload."""
    name = models.CharField(max_length=200, null=False)
    description = models.TextField(null=True)
    image_url = models.TextField(null=True)
    required_integrations = models.ManyToManyField(Integration, blank=True)
    possible_payloads = models.ManyToManyField(Payload, blank=True)
    users = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.name
