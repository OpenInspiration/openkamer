# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-07 18:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('document', '0026_auto_20170307_1532'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='source_url',
            field=models.URLField(default=''),
            preserve_default=False,
        ),
    ]