# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-27 11:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('document', '0015_auto_20161125_1936'),
    ]

    operations = [
        migrations.AlterField(
            model_name='besluitenlijst',
            name='url',
            field=models.URLField(max_length=400),
        ),
    ]