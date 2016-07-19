# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oai.models


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0008_add_index_on_last_modified'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApiKey',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(default=oai.models.fresh_api_key, unique=True, max_length=64)),
                ('name', models.CharField(unique=True, max_length=128)),
            ],
        ),
    ]
