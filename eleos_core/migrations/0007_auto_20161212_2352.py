# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-12 23:52
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eleos_core', '0006_auto_20161212_2311'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='payload',
            options={'ordering': ['length']},
        ),
    ]