# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-14 01:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eleos_core', '0002_auto_20161214_0052'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activeintegration',
            name='external_user_id',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='Unique ID of User in External Service.'),
        ),
    ]