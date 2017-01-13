# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-13 02:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eleos_core', '0016_auto_20161230_0108'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='giftedmoment',
            name='context',
        ),
        migrations.AddField(
            model_name='giftedmoment',
            name='delay',
            field=models.IntegerField(blank=True, default=0, verbose_name='The amount of time, in seconds, to wait after the Checkin before delivering the Moment.'),
        ),
        migrations.AddField(
            model_name='giftedmoment',
            name='deliver_datetime',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='Deliver Moment at exactly this date and time.'),
        ),
        migrations.AddField(
            model_name='giftedmoment',
            name='trigger',
            field=models.CharField(choices=[('Swarm', 'Swarm Checkin'), ('Datetime', 'Time & Date')], default='Swarm', max_length=8, verbose_name='The event that should trigger delivery of the Moment.'),
        ),
        migrations.AddField(
            model_name='giftedmoment',
            name='venue_type',
            field=models.CharField(blank=True, choices=[('4d4b7104d754a06370d81259', 'Arts & Entertainment'), ('4d4b7105d754a06372d81259', 'College & University'), ('4d4b7105d754a06373d81259', 'Event'), ('4d4b7105d754a06374d81259', 'Food'), ('4d4b7105d754a06376d81259', 'Nightlife Spot'), ('4d4b7105d754a06377d81259', 'Outdoors & Recreation'), ('4d4b7105d754a06375d81259', 'Professional & Other Places'), ('4e67e38e036454776db1fb3a', 'Residence'), ('4d4b7105d754a06378d81259', 'Shop & Service'), ('4d4b7105d754a06379d81259', 'Travel & Transport')], default=None, max_length=24, null=True, verbose_name='Only trigger at this type of Checkin.'),
        ),
    ]