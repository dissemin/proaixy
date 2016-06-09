# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0007_sort_by_last_modified'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oairecord',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
    ]
