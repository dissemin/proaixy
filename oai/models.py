# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from lxml import etree

from django.db import models
from django.db.models import F
from django.utils.functional import cached_property
from django.utils.html import escape
from django.core.exceptions import ObjectDoesNotExist
from djcelery.models import TaskMeta, PeriodicTask, TaskState

import hashlib

from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry

from oai.utils import nstr, ndt
from oai.settings import OWN_SET_PREFIX, RESUMPTION_TOKEN_SALT

# An OAI data provider
class OaiSource(models.Model):
    # The URL of the OAI endpoint
    url = models.URLField(max_length=256, unique=True) 
    # The name of the repository as exposed by Identify
    name = models.CharField(max_length=100, unique=True)
    # The prefix used for the virtual sets
    prefix = models.CharField(max_length=100, unique=True)
    # The optional set restrincting the records to harvest
    restrict_set = models.CharField(max_length=512, null=True, blank=True)
    # Records with a modification date earlier than that are already fetched
    last_update = models.DateTimeField() 
    # True if the endpoint does not store datetimes but only dates
    day_granularity = models.BooleanField(default=True) 
    # True if the endpoint only supports GET requests
    get_method = models.BooleanField(default=False) 

    # Task id of the harvester
    harvester = models.CharField(max_length=128, null=True, blank=True)
    # Status of the harvester
    status = models.CharField(max_length=256, null=True, blank=True) 
    # Cached number of records belonging to this source
    nb_records = models.IntegerField(default=0)
    # Last change made to this model
    last_change = models.DateTimeField(auto_now=True) 
    def __unicode__(self):
        return self.name
    def getClient(self):
        registry = MetadataRegistry()
        client = Client(self.url, registry)
        client.get_method = self.get_method
        client._day_granularity = self.day_granularity
        return client
    def sets(self):
        return OaiSet.objects.filter(source=self.pk)
    def records(self):
        return OaiRecord.objects.filter(source=self.pk)
    def harvesting(self):
        return not (self.harvesterState() in ['SUCCESS', 'FAILURE', 'REVOKED', 'DELETED'])
    @cached_property
    def task(self):
        try:
            return TaskMeta.objects.get(task_id=self.harvester)
        except ObjectDoesNotExist:
            pass
    def harvesterState(self):
        if self.task:
            return self.task.status
        return 'DELETED'
    def syncNbRecords(self):
        """
        Synchronize the cached number of records.
        This number is supposed to be updated when records
        are created and deleted, but it might go out of sync sometimes.
        """
        OaiSource.objects.filter(pk=self.pk).update(nb_records=OaiRecord.objects.filter(source=self.pk).count())
    def incrementNbRecords(self):
        """
        Atomically increment the cached number of records
        """
        OaiSource.objects.filter(pk=self.pk).update(nb_records=F('nb_records')+1)
    def decrementNbRecords(self):
        OaiSource.objects.filter(pk=self.pk).update(nb_records=F('nb_records')-1)


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
    name = models.CharField(max_length=2048, db_index=True)
    fullname = models.CharField(max_length=2048, null=True, blank=True)

    unique_together = ('name','source')

    def __unicode__(self):
        prefix = OWN_SET_PREFIX
        if self.source:
            prefix = self.source.prefix
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
            if prefix != OWN_SET_PREFIX:
                source = OaiSource.objects.get(prefix=prefix)
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

# Lazy conversion from OaiFormat.pk to OaiFormat.identifier
# This function is called once per rendered record, so
# prefetching once the list of OaiFormats is cheaper.
oaiformats_cache = None

def getOaiFormatName(pk):
    global oaiformats_cache
    if oaiformats_cache is None:
        oaiformats_cache = {k:v for (k,v) in OaiFormat.objects.all().values('pk','name')}
    try:
        return oaiformats_cache[pk]
    except KeyError:
        return OaiFormat.objects.get(pk=pk).name


from oai.virtual import REGISTERED_EXTRACTORS

# A record from an OAI source
class OaiRecord(models.Model):
    source = models.ForeignKey(OaiSource)
    # Last modified by the OAI source
    timestamp = models.DateTimeField(db_index=True)
    # The format of the metadata
    format = models.ForeignKey(OaiFormat)
    # The unique ID of the metadata from the source
    identifier = models.CharField(max_length=256, unique=True)
    # The fingerprint of this paper (title + sometimes year and/or authors last names)
    fingerprint = models.CharField(max_length=64, db_index=True, null=True)
    # The DOI of this paper (if provided)
    doi = models.CharField(max_length=512, db_index=True, null=True, blank=True)
    # The sets it belongs to
    sets = models.ManyToManyField(OaiSet)
    # The metadata as an XML object
    metadata = models.TextField()
    # Last updated by us
    last_modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.identifier

    def render_metadata(self):
        """
        Render the metadata, to be included in the
        output of the OAI interface
        """
        # If that's already plain XML, just include it
        try:
            etree.fromstring(self.metadata)
            return self.metadata
        except etree.XMLSyntaxError as e:
            pass

        # Otherwise wrap it inside the appropriate OAI tags
        return ('<metadata xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">%s</metadata>' % escape(self.metadata))

    def get_virtual_sets(self):
        """
        Returns the list of virtual sets for this extractor
        """
        try:
            fullXML = etree.fromstring(self.metadata)
        except etree.XMLSyntaxError as e:
            return

        for extractor in REGISTERED_EXTRACTORS:
            if self.format.name in extractor.formats():
                sets = extractor.getVirtualSets(fullXML, self.source)
                # print "Sets for "+identifier+": "+str(sets)
                for set in sets:
                    if not set:
                        continue
                    name = extractor.subset()+':'+set
                    yield name

    @property
    def format_name(self):
        """
        Returns the identifier of the format without fetching
        the OaiFormat
        """
        return getOaiFormatName(self.format_id)

# A resumption token for the output interface
class ResumptionToken(models.Model):
    date_created = models.DateTimeField(auto_now=True)
    queryType = models.CharField(max_length=64)
    set = models.ForeignKey(OaiSet, null=True, blank=True)
    metadataPrefix = models.ForeignKey(OaiFormat, null=True, blank=True)
    fro = models.DateTimeField(null=True, blank=True)
    until = models.DateTimeField(null=True, blank=True)
    firstpk = models.IntegerField()
    key = models.CharField(max_length=128, null=True, blank=True)
    def __unicode__(self):
        return self.key
    def genkey(self):
        m = hashlib.md5()
        m.update('%s_%s_%d_%s_%s_%s_%s_%d' % (RESUMPTION_TOKEN_SALT, ndt(self.date_created),
                        self.id, nstr(self.set), self.metadataPrefix,
                        ndt(self.fro), ndt(self.until), self.firstpk))
        self.key = m.hexdigest()
        self.save(update_fields=['key'])



