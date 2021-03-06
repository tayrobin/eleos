# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-22 00:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eleos_core', '0005_auto_20161214_1217'),
    ]

    operations = [
        migrations.AddField(
            model_name='activeintegration',
            name='expires_in',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='Length of time, in seconds, that access_token is valid for.'),
        ),
        migrations.AddField(
            model_name='activeintegration',
            name='next_sync_token',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='A bookmark for Google Calendar events.'),
        ),
        migrations.AddField(
            model_name='activeintegration',
            name='refresh_token',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='Token to refresh access_token after expiration.'),
        ),
        migrations.AddField(
            model_name='activeintegration',
            name='resource_id',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='The ID of the external resource (i.e. the Calendar ID).'),
        ),
        migrations.AddField(
            model_name='activeintegration',
            name='resource_uri',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='The URI to which the access_token grants access.'),
        ),
        migrations.AddField(
            model_name='activeintegration',
            name='resource_uuid',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='My UUID for the resource, created upon activation.'),
        ),
        migrations.AddField(
            model_name='activeintegration',
            name='token_type',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='Permissions to which the access_token grants access.'),
        ),
    ]
