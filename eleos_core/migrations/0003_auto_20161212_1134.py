# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-12 11:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eleos_core', '0002_auto_20161212_1129'),
    ]

    operations = [
        migrations.AlterField(
            model_name='integration',
            name='auth_url',
            field=models.CharField(default=None, max_length=200),
        ),
    ]