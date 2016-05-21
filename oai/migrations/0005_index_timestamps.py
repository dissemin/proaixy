# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0004_longer_identifier'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oairecord',
            name='timestamp',
            field=models.DateTimeField(db_index=True),
        ),
    ]
