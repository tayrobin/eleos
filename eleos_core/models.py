from __future__ import unicode_literals
import arrow
import logging
import datetime
from django.db import models
from django.utils import timezone
from timezone_field import TimeZoneField
from django.contrib.auth.models import User

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.INFO)


class Integration(models.Model):
    """"A service that provides information on the User's daily schedule."""
    name = models.CharField(max_length=200, blank=False)
    description = models.TextField(blank=True, default=None, null=True)
    image_url = models.TextField(blank=True, default=None, null=True)
    auth_url = models.TextField(blank=True, default=None, null=True)
    token_url = models.TextField(blank=True, default=None, null=True)
    users = models.ManyToManyField(
        User, through='ActiveIntegration', blank=True)

    def __unicode__(self):
        return self.name


class Payload(models.Model):
    """"What gets delivered to the User in a Moment."""
    name = models.CharField(max_length=200, blank=False)
    description = models.TextField(blank=True, default=None, null=True)
    image_url = models.TextField(blank=True, default=None, null=True)
    length = models.DurationField(
        "The expected length of time, in seconds, Payload will fill.", blank=True, default=None, null=True)
    deliverable_url = models.TextField(blank=True, default=None, null=True)

    class Meta:
        ordering = ['length']

    def __unicode__(self):
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

    def __unicode__(self):
        return self.name


class ActiveIntegration(models.Model):
    """An active connection between a User and an Integration that they've authorized."""
    user = models.ForeignKey(User)
    integration = models.ForeignKey(Integration)
    access_token = models.TextField(blank=True, default=None, null=True)
    access_token_secret = models.TextField(blank=True, default=None, null=True)
    external_user_id = models.TextField(
        "Unique ID of User in External Service.", blank=True, default=None, null=True)

    # adding details for Google Calendar integration
    refresh_token = models.TextField(
        "Token to refresh access_token after expiration.", blank=True, default=None, null=True)
    expires_in = models.TextField(
        "Length of time, in seconds, that access_token is valid for.", blank=True, default=None, null=True)
    token_type = models.TextField(
        "Permissions to which the access_token grants access.", blank=True, default=None, null=True)
    resource_uri = models.TextField(
        "The URI to which the access_token grants access.", blank=True, default=None, null=True)
    resource_id = models.TextField(
        "The ID of the external resource (i.e. the Calendar ID).", blank=True, default=None, null=True)
    resource_uuid = models.TextField(
        "My UUID for the resource, created upon activation.", blank=True, default=None, null=True)
    next_sync_token = models.TextField(
        "A bookmark for Google Calendar events.", blank=True, default=None, null=True)

    def __unicode__(self):
        return "%s <--> %s" % (self.user.username, self.integration.name)


class OAuthCredentials(models.Model):
    """A generated Token/Secret credential pair for an OAuth Integration."""
    request_token = models.TextField(blank=True, default=None, null=True)
    request_token_secret = models.TextField(
        blank=True, default=None, null=True)


class GiftedMoment(models.Model):
    """A Moment created by one User for another User at a specific time/place/context."""
    creator = models.ForeignKey(User, related_name='creator')
    recipient = models.ForeignKey(User, related_name='recipient')
    payload = models.ForeignKey(Payload)
    endorsement = models.TextField(blank=True, default=None, null=True)

    # trigger
    TRIGGER_CHOICES = (
        ('Swarm', 'Swarm Checkin'),
        # TODO: ('Calendar', 'Calendar Event'),
        ('Datetime', 'Time & Date')
    )

    trigger = models.CharField("The event that should trigger delivery of the Moment.",
                               choices=TRIGGER_CHOICES,
                               max_length=8,
                               blank=False,
                               default='Swarm'
                               )

    # datetime filters (really just a picker)
    deliver_datetime = models.DateTimeField("Deliver Moment at exactly this date and time.",
                                            blank=True, null=True, default=None
                                            )
    datetime_task_queued = models.BooleanField(
        default=False, editable=False
    )

    # swarm filters
    delay = models.IntegerField(
        "The amount of time, in seconds, to wait after the Checkin before delivering the Moment.", default=0, blank=True)

    VENUE_TYPE_CHOICES = (
        ('4d4b7104d754a06370d81259', 'Arts & Entertainment'),
        ('4d4b7105d754a06372d81259', 'College & University'),
        ('4d4b7105d754a06373d81259', 'Event'),
        ('4d4b7105d754a06374d81259', 'Food'),
        ('4d4b7105d754a06376d81259', 'Nightlife Spot'),
        ('4d4b7105d754a06377d81259', 'Outdoors & Recreation'),
        ('4d4b7105d754a06375d81259', 'Professional & Other Places'),
        ('4e67e38e036454776db1fb3a', 'Residence'),
        ('4d4b7105d754a06378d81259', 'Shop & Service'),
        ('4d4b7105d754a06379d81259', 'Travel & Transport')
    )

    venue_type = models.CharField("Only trigger at this type of Checkin.",
                                  choices=VENUE_TYPE_CHOICES,
                                  max_length=24,
                                  blank=True, null=True,
                                  default=None
                                  )

    # TODO: calendar filters

    # FBM tracking
    fbm_message_id = models.TextField(
        blank=True, default=None, null=True, editable=False)
    fbm_sent_status = models.BooleanField(default=False, editable=False)
    fbm_message_sent_at = models.DateTimeField(
        default=None, editable=False, null=True)
    fbm_read_status = models.BooleanField(default=False, editable=False)
    fbm_message_read_at = models.DateTimeField(
        default=None, editable=False, null=True)
    fbm_payload_click_at = models.DateTimeField(
        default=None, editable=False, null=True)
    fbm_payload_click_status = models.BooleanField(
        default=False, editable=False)
    fbm_payload_click_count = models.IntegerField(default=0, editable=False)

    # auto-timestamps
    created_at = models.DateTimeField(editable=False)
    updated_at = models.DateTimeField(editable=False)

    def save(self, *args, **kwargs):
        """On save, update timestamps, and queue Datetime-trigged GiftedMoments."""
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()

        # queue datetime Moments
        if self.trigger == 'Datetime' and not self.datetime_task_queued:
            from .foursquare_views import giveGiftedMoment
            logging.info("Queueing Datetime-trigged GiftedMoment.")
            # localize to recipient's timezone
            deliver_time = arrow.get(self.deliver_datetime, self.recipient.residence.home_time_zone.zone)
            giveGiftedMoment.apply_async(
                kwargs={'user_id': self.recipient.id, 'id': self.id}, eta=deliver_time)
            self.datetime_task_queued = True

        return super(GiftedMoment, self).save(*args, **kwargs)

    def __unicode__(self):
        return "%s recommends %s to %s." % (self.creator, self.payload, self.recipient)


class Residence(models.Model):
    "Model for extending a User to include their timezone."
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    home_time_zone = TimeZoneField(default='US/Pacific')
