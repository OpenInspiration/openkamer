# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-27 09:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('document', '0046_auto_20170324_1647'),
    ]

    operations = [
        migrations.AddField(
            model_name='kamerstuk',
            name='type',
            field=models.CharField(choices=[('Motie', 'Motie'), ('Amendement', 'Amendement'), ('Wetsvoorstel', 'Wetsvoorstel'), ('Verslag', 'Verslag'), ('Nota', 'Nota'), ('Brief', 'Brief'), ('Onbekend', 'Onbekend')], db_index=True, default='Onbekend', max_length=30),
        ),
    ]
