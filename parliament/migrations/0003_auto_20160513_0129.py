# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-12 23:29
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parliament', '0002_auto_20160513_0124'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='politicalparty',
            options={'verbose_name_plural': 'Political parties'},
        ),
    ]
