# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
import hashlib

from oai.utils import nstr, ndt

salt = 'change_me'

# An OAI data provider
class OaiSource(models.Model):
    url = models.URLField(max_length=256)
    name = models.CharField(max_length=100)
    last_update = models.DateTimeField()

    def __unicode__(self):
        return self.name

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
    name = models.CharField(max_length=128)
    fullname = models.CharField(max_length=128, null=True, blank=True)
    def __unicode__(self):
        prefix = 'proaixy'
        if self.source:
            prefix = self.source.name
        return prefix+':'+self.name


# A record from an OAI source
class OaiRecord(models.Model):
    source = models.ForeignKey(OaiSource)
    # Last modified by the OAI source
    timestamp = models.DateTimeField()
    # The format of the metadata
    format = models.CharField(max_length=128)
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
    metadataPrefix = models.CharField(max_length=128, null=True, blank=True)
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

