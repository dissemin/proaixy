# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0006_more_efficient_resumption'),
    ]

    operations = [
        migrations.AddField(
            model_name='resumptiontoken',
            name='first_timestamp',
            field=models.DateTimeField(default=datetime.datetime(2016, 6, 3, 17, 11, 50, 857760, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AlterIndexTogether(
            name='oairecord',
            index_together=set([('last_modified', 'id')]),
        ),
    ]
