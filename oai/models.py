# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from djcelery.models import TaskMeta, PeriodicTask, TaskState

import hashlib

from oai.utils import nstr, ndt
from oai.settings import own_set_prefix

salt = 'change_me'

# An OAI data provider
class OaiSource(models.Model):
    url = models.URLField(max_length=256, unique=True)
    name = models.CharField(max_length=100, unique=True)
    last_update = models.DateTimeField()
    day_granularity = models.BooleanField()

    harvester = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=256, null=True, blank=True)
    last_change = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return self.name
    def sets(self):
        return OaiSet.objects.filter(source=self.pk)
    def records(self):
        return OaiRecord.objects.filter(source=self.pk)
    def harvesting(self):
        return not (self.harvesterState() in ['SUCCESS', 'FAILURE', 'REVOKED', 'DELETED'])
    def harvesterTask(self):
        try:
            return TaskMeta.objects.get(task_id=self.harvester)
        except ObjectDoesNotExist:
            pass
    def harvesterState(self):
        task = self.harvesterTask()
        if task:
            return task.status
        return 'DELETED'

# An error encountered while harvesting an OAI data provider
class OaiError(models.Model):
    source = models.ForeignKey(OaiSource)
    timestamp = models.DateTimeField(auto_now=True)
    text = models.CharField(max_length=512, null=True, blank=True)
    def __unicode__(self):
        return self.text

# An OAI set. If it is not associated with a source, it means that it is introduced by us
class OaiSet(models.Model):
    source = models.ForeignKey(OaiSource, null=True, blank=True)
    name = models.CharField(max_length=512)
    fullname = models.CharField(max_length=512, null=True, blank=True)

    unique_together = ('name','source')

    def __unicode__(self):
        prefix = own_set_prefix
        if self.source:
            prefix = self.source.name
        return prefix+':'+self.name
    @staticmethod
    def byRepresentation(name):
        """
        Returns the set s such that unicode(s) == name, or None if not found
        """
        scpos = name.find(':')
        if scpos == -1:
            return None
        prefix = name[:scpos]
        try:
            if prefix != own_set_prefix:
                source = OaiSource.objects.get(name=prefix)
            else:
                source = None
            return OaiSet.objects.get(source=source,name=name[scpos+1:])
        except ObjectDoesNotExist:
            return None

class OaiFormat(models.Model):
    name = models.CharField(max_length=128)
    schema = models.CharField(max_length=512, null=True, blank=True)
    namespace = models.CharField(max_length=512, null=True, blank=True)
    def __unicode__(self):
        return self.name

# A record from an OAI source
class OaiRecord(models.Model):
    source = models.ForeignKey(OaiSource)
    # Last modified by the OAI source
    timestamp = models.DateTimeField()
    # The format of the metadata
    format = models.ForeignKey(OaiFormat)
    # The unique ID of the metadata from the source
    identifier = models.CharField(max_length=128, unique=True)
    # The sets it belongs to
    sets = models.ManyToManyField(OaiSet)
    # The metadata as an XML object
    metadata = models.TextField()
    # Last updated by us
    last_modified = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return self.identifier

# A resumption token for the output interface
class ResumptionToken(models.Model):
    date_created = models.DateTimeField(auto_now=True)
    queryType = models.CharField(max_length=64)
    set = models.ForeignKey(OaiSet, null=True, blank=True)
    metadataPrefix = models.ForeignKey(OaiFormat, null=True, blank=True)
    fro = models.DateTimeField(null=True, blank=True)
    until = models.DateTimeField(null=True, blank=True)
    offset = models.IntegerField()
    cursor = models.IntegerField()
    total_count = models.IntegerField()
    key = models.CharField(max_length=128, null=True, blank=True)
    def __unicode__(self):
        return self.key
    def genkey(self):
        m = hashlib.md5()
        m.update('%s_%s_%d_%s_%s_%s_%s_%d' % (salt, ndt(self.date_created),
                        self.id, nstr(self.set), self.metadataPrefix,
                        ndt(self.fro), ndt(self.until), self.offset))
        self.key = m.hexdigest()
        self.save()


    
# A statement that some record belongs to some set.
# class OaiSetSpec(models.Model):
#    container = models.ForeignKey(OaiSet)
#    record = models.ForeignKey(OaiRecord)
#    unique_together
#    def __unicode__(self):
#        return record.identifier + " is " + unicode(self.container)

