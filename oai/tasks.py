# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from celery import shared_task
from celery.utils.log import get_task_logger
from celery import current_task, task

from lxml import etree
from urllib2 import URLError, HTTPError

from django.utils.timezone import now, make_aware, make_naive, UTC
from django.db import IntegrityError, transaction
from datetime import timedelta

from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry, oai_dc_reader
from oaipmh.datestamp import tolerant_datestamp_to_datetime
from oaipmh.error import ErrorBase, DatestampError, NoRecordsMatchError, XMLSyntaxError

from oai.models import *
from oai.settings import *

logger = get_task_logger(__name__)

def addSourceFromURL(url, prefix):
    try:
        registry = MetadataRegistry()
        client = Client(url, registry)
        identify = client.identify()
        name = identify.repositoryName()
        last_update = make_aware(identify.earliestDatestamp(), UTC())
        day_granularity = (identify.granularity() == 'YYYY-MM-DD')
        try:
            source = OaiSource(url=url, name=name, prefix=prefix,
                    last_update=last_update, day_granularity=day_granularity)
            source.save()
        except IntegrityError as e:
            return str(e)
    except (ErrorBase, URLError, HTTPError) as e:
        return unicode(e)
    except XMLSyntaxError as e:
        return 'XML syntax error: '+unicode(e)
        
@task(serializer='json',bind=True)
def fetch_from_source(self, pk):
    self.update_state(state='PROGRESS')

    source = OaiSource.objects.get(pk=pk)
    baseStatus = 'records'

    # Set up the OAI fetcher
    format, created = OaiFormat.objects.get_or_create(name=metadata_format) # defined in oai.settings
    registry = MetadataRegistry()
    registry.registerReader(format.name, oai_dc_reader)
    client = Client(source.url, registry)
    client._day_granularity = source.day_granularity

    # Limit queries to records in a time range of 7 days (by default)
    time_chunk = query_time_range

    start_date = make_naive(source.last_update, UTC())
    current_date = make_naive(now(), UTC())
    until_date = start_date + time_chunk

    while start_date <= current_date:
        source.status = baseStatus+' between '+str(start_date)+' and '+str(until_date)
        source.save()
        try:
            listRecords = client.listRecords(metadataPrefix=format.name, from_=start_date, until=until_date)
        except NoRecordsMatchError:
            listRecords = []

        # Small hack to commit the database every NB_RECORDS_BEFORE_COMMIT
        recordFound = True
        while recordFound:
            i = 0
            recordFound = False
            with transaction.atomic():
                for record in listRecords:
                    recordFound = True
                    update_record(source, record, format)
                    i += 1
                    if i > NB_RECORDS_BEFORE_COMMIT:
                        break

        source.last_update = make_aware(min(until_date, current_date), UTC())
        source.save()
        until_date += time_chunk
        start_date += time_chunk
        #except Exception as e:
    #    error = OaiError(source=source, text=unicode(e))
    #    error.save()

@task(serializer='json',bind=True)
def fetch_sets_from_source(self, pk):
    self.update_state(state='PROGRESS')

    source = OaiSource.objects.get(pk=pk)
    baseStatus = 'sets'

    registry = MetadataRegistry()
    client = Client(source.url, registry)
    
    listSets = client.listSets()
    for set in listSets:
        s, created = OaiSet.objects.get_or_create(source=source, name=set[0])
        s.fullname=set[1]
        s.save()

@task(serializer='json',bind=True)
def fetch_formats_from_source(self, pk):
    self.update_state(state='PROGRESS')

    source = OaiSource.objects.get(pk=pk)
    source.harvester = self.request.id
    baseStatus = 'formats'
    source.status = baseStatus
    source.save()

    registry = MetadataRegistry()
    client = Client(source.url, registry)
    
    listFormats = client.listMetadataFormats()
    for format in listFormats:
        f, created = OaiFormat.objects.get_or_create(name=format[0])
        f.schema=format[1]
        f.namespace=format[2]
        f.save()

@transaction.atomic
def update_record(source, record, format):
    fullXML = record[1].element()
    metadataStr = etree.tostring(fullXML, pretty_print=True)
    identifier = record[0].identifier()
    timestamp = record[0].datestamp()
    timestamp = make_aware(timestamp, UTC())

    modelrecord, created = OaiRecord.objects.get_or_create(identifier=identifier, format=format,
            defaults={'source':source, 'metadata':metadataStr, 'timestamp':timestamp})
    if not created:
        modelrecord.timestamp = timestamp
        modelrecord.metadata = metadataStr
        modelrecord.save()

    # Add regular sets
    for s in record[0].setSpec():
        modelset, created = OaiSet.objects.get_or_create(source=source, name=s)
        modelrecord.sets.add(modelset)

    # Apply virtual set extractors
    for extractor in extractors:
        if extractor.format() == format.name:
            sets = extractor.getVirtualSets(fullXML)
            # print "Sets for "+identifier+": "+str(sets)
            for set in sets:
                name = extractor.subset()+':'+set
                modelset, created = OaiSet.objects.get_or_create(name=name)
                modelrecord.sets.add(modelset)
            sets = None


@shared_task
def cleanup_resumption_tokens():
    threshold = now() - resumption_token_validity
    ResumptionToken.objects.filter(date_created__lt=threshold).delete()



