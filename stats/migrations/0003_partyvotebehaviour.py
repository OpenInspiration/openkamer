# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-28 09:37
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parliament', '0004_politicalparty_current_parliament_seats'),
        ('government', '0003_auto_20161226_1012'),
        ('stats', '0002_auto_20161226_1015'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartyVoteBehaviour',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voting_type', models.CharField(choices=[('ALL', 'Alle'), ('BILL', 'Wetsvoorstel'), ('OTHER', 'Overig (Motie, Amendement)')], max_length=5)),
                ('votes_for', models.IntegerField()),
                ('votes_against', models.IntegerField()),
                ('votes_none', models.IntegerField()),
                ('government', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='government.Government')),
                ('party', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='parliament.PoliticalParty')),
                ('submitter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='party_vote_behaviour_submitter', to='parliament.PoliticalParty')),
            ],
        ),
    ]