# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-27 11:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('document', '0016_auto_20161127_1200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='besluitenlijst',
            name='url',
            field=models.URLField(max_length=1000),
        ),
    ]
