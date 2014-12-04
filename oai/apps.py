# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from oai.models import *
from django.apps import AppConfig
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

@receiver(post_save, sender=OaiRecord)
def post_save_callback(sender, **kwargs):
    if kwargs['created']:
        sender.source.incrementNbRecords()

@receiver(post_delete, sender=OaiRecord)
def post_delete_callback(sender, **kwargs):
    sender.source.decrementNbRecords()

class OaiConfig(AppConfig):
    name = 'oai'

