# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OaiError',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('text', models.CharField(max_length=512, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='OaiFormat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('schema', models.CharField(max_length=512, null=True, blank=True)),
                ('namespace', models.CharField(max_length=512, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='OaiRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField()),
                ('identifier', models.CharField(unique=True, max_length=128)),
                ('metadata', models.TextField()),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('format', models.ForeignKey(to='oai.OaiFormat')),
            ],
        ),
        migrations.CreateModel(
            name='OaiSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2048, db_index=True)),
                ('fullname', models.CharField(max_length=2048, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='OaiSource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(unique=True, max_length=256)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('prefix', models.CharField(unique=True, max_length=100)),
                ('restrict_set', models.CharField(max_length=512, null=True, blank=True)),
                ('last_update', models.DateTimeField()),
                ('day_granularity', models.BooleanField(default=True)),
                ('get_method', models.BooleanField(default=False)),
                ('harvester', models.CharField(max_length=128, null=True, blank=True)),
                ('status', models.CharField(max_length=256, null=True, blank=True)),
                ('nb_records', models.IntegerField(default=0)),
                ('last_change', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ResumptionToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now=True)),
                ('queryType', models.CharField(max_length=64)),
                ('fro', models.DateTimeField(null=True, blank=True)),
                ('until', models.DateTimeField(null=True, blank=True)),
                ('offset', models.IntegerField()),
                ('cursor', models.IntegerField()),
                ('total_count', models.IntegerField()),
                ('key', models.CharField(max_length=128, null=True, blank=True)),
                ('metadataPrefix', models.ForeignKey(blank=True, to='oai.OaiFormat', null=True)),
                ('set', models.ForeignKey(blank=True, to='oai.OaiSet', null=True)),
            ],
        ),
        migrations.AddField(
            model_name='oaiset',
            name='source',
            field=models.ForeignKey(blank=True, to='oai.OaiSource', null=True),
        ),
        migrations.AddField(
            model_name='oairecord',
            name='sets',
            field=models.ManyToManyField(to='oai.OaiSet'),
        ),
        migrations.AddField(
            model_name='oairecord',
            name='source',
            field=models.ForeignKey(to='oai.OaiSource'),
        ),
        migrations.AddField(
            model_name='oaierror',
            name='source',
            field=models.ForeignKey(to='oai.OaiSource'),
        ),
    ]
