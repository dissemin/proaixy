# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='oairecord',
            name='doi',
            field=models.CharField(db_index=True, max_length=512, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='oairecord',
            name='fingerprint',
            field=models.CharField(max_length=64, null=True, db_index=True),
        ),
    ]
