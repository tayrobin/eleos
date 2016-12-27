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
    deliverable_url = models.TextField(blank=True, default=None, null=True)

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
    access_token_secret = models.TextField(blank=True, default=None, null=True)
    external_user_id = models.TextField("Unique ID of User in External Service.", blank=True, default=None, null=True)

    # adding details for Google Calendar integration
    refresh_token = models.TextField("Token to refresh access_token after expiration.", blank=True, default=None, null=True)
    expires_in = models.TextField("Length of time, in seconds, that access_token is valid for.", blank=True, default=None, null=True)
    token_type = models.TextField("Permissions to which the access_token grants access.", blank=True, default=None, null=True)
    resource_uri = models.TextField("The URI to which the access_token grants access.", blank=True, default=None, null=True)
    resource_id = models.TextField("The ID of the external resource (i.e. the Calendar ID).", blank=True, default=None, null=True)
    resource_uuid = models.TextField("My UUID for the resource, created upon activation.", blank=True, default=None, null=True)
    next_sync_token = models.TextField("A bookmark for Google Calendar events.", blank=True, default=None, null=True)

    def __str__(self):
        return "%s <--> %s" % (self.user.username, self.integration.name)


class OAuthCredentials(models.Model):
    """A generated Token/Secret credential pair for an OAuth Integration."""
    request_token = models.TextField(blank=True, default=None, null=True)
    request_token_secret = models.TextField(blank=True, default=None, null=True)


class GiftedMoment(models.Model):
    """A Moment created by one User for another User at a specific time/place/context."""
    creator = models.ManyToManyField(User, blank=False, related_name="creator")
    recipient = models.ManyToManyField(User, blank=False, related_name="recipient")
    payload = models.ManyToManyField(Payload, blank=False)
    endorsement = models.TextField(blank=True, default=None, null=True)

    CONTEXT_CHOICES = (
        ('PRD', 'Productivity'),
        ('ENT', 'Entertainment'),
        ('INS', 'Inspiration'),
        ('EDU', 'Education'),
    )
    context = models.CharField(
        max_length=3,
        choices=CONTEXT_CHOICES,
        default='ENT',
    )

    def __str__(self):
        return "%(creator)s recommends %(payload)s to %(recipient)s." % {'creator': self.creator.name, 'payload': self.payload.name, 'recipient': self.recipient.name}
        