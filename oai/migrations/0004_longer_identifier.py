# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0003_add_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oairecord',
            name='identifier',
            field=models.CharField(unique=True, max_length=256),
        ),
    ]
