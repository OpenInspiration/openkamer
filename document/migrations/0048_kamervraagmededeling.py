# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-08 10:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('document', '0047_kamerstuk_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='KamervraagMededeling',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vraagnummer', models.CharField(db_index=True, max_length=200)),
                ('text', models.TextField()),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='document.Document')),
                ('kamervraag', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='document.Kamervraag')),
            ],
        ),
    ]
