# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0005_index_timestamps'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resumptiontoken',
            old_name='cursor',
            new_name='firstpk',
        ),
        migrations.RemoveField(
            model_name='resumptiontoken',
            name='offset',
        ),
        migrations.RemoveField(
            model_name='resumptiontoken',
            name='total_count',
        ),
    ]
