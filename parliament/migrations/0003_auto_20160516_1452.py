# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-16 12:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parliament', '0002_auto_20160516_0020'),
    ]

    operations = [
        migrations.AddField(
            model_name='politicalparty',
            name='name_short',
            field=models.CharField(default='', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='politicalparty',
            name='wikimedia_logo_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='politicalparty',
            name='wikipedia_url',
            field=models.URLField(blank=True),
        ),
    ]