# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oai', '0009_apikey'),
    ]

    operations = [
        migrations.AddField(
            model_name='oaisource',
            name='format',
            field=models.CharField(default='oai_dc', max_length=100),
        ),
    ]
