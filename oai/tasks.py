# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from celery import shared_task
from celery.utils.log import get_task_logger
from celery import current_task

from lxml import etree

from django.utils.timezone import now, make_aware, make_naive, UTC
from datetime import timedelta

from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry, oai_dc_reader
from oaipmh.datestamp import tolerant_datestamp_to_datetime
from oaipmh.error import DatestampError, NoRecordsMatchError

from oai.models import *

logger = get_task_logger(__name__)

@shared_task
def fetch_from_source(pk):
    source = OaiSource.objects.get(pk=pk)
    #try:
    # Set up the OAI fetcher
    registry = MetadataRegistry()
    registry.registerReader('oai_dc', oai_dc_reader)
    client = Client(source.url, registry)
    client.updateGranularity()

    # Limit queries to records in a time range of 7 days
    time_chunk = timedelta(days=2)

    start_date = make_naive(source.last_update, UTC())
    current_date = make_naive(now(), UTC())
    until_date = start_date + time_chunk

    while start_date <= current_date:
        print "Fetching records between "+str(start_date)+" and "+str(until_date)
        try:
            listRecords = client.listRecords(metadataPrefix='oai_dc', from_=start_date, until=until_date)
        except NoRecordsMatchError:
            listRecords = []

        for record in listRecords:
            update_record(source, record)

        source.last_update = make_aware(until_date, UTC())
        source.save()
        until_date += time_chunk
        start_date += time_chunk
        #except Exception as e:
    #    error = OaiError(source=source, text=unicode(e))
    #    error.save()

def update_record(source, record):
    fullXML = record[1].element()
    metadataStr = etree.tostring(fullXML, pretty_print=True)
    identifier = record[0].identifier()
    timestamp = record[0].datestamp()
    timestamp = make_aware(timestamp, UTC())

    modelrecord, created = OaiRecord.objects.get_or_create(identifier=identifier,
            defaults={'source':source, 'metadata':metadataStr, 'timestamp':timestamp})
    if not created:
        modelrecord.timestamp = timestamp
        modelrecord.metadata = metadataStr
        modelrecord.save()
    for s in record[0].setSpec():
        modelset, created = OaiSet.objects.get_or_create(source=source, name=s)
        modelrecord.sets.add(modelset)



