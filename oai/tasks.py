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
from time import sleep
from bulk_update.helper import bulk_update

from oaipmh.metadata import oai_dc_reader, base_dc_reader
from oaipmh.datestamp import tolerant_datestamp_to_datetime
from oaipmh.error import ErrorBase, BadVerbError, DatestampError, NoRecordsMatchError, XMLSyntaxError

from oai.models import *
from oai.settings import *
from oai.virtual import *

logger = get_task_logger(__name__)

def fill_extra_ids(record):
    element = etree.fromstring(record.metadata)

    doi = extract_doi(element)
    fingerprint = compute_fingerprint(element)

    if doi or fingerprint:
        record.doi = doi
        record.fingerprint = fingerprint
        record.save(update_fields=['doi','fingerprint'])

def addSourceFromURL(url, prefix, get_method=False):
    try:
        registry = MetadataRegistry()
        client = Client(url, registry)
        client.get_method = get_method
        identify = client.identify()
        name = identify.repositoryName()
        last_update = make_aware(identify.earliestDatestamp(), UTC())
        day_granularity = (identify.granularity() == 'YYYY-MM-DD')
        try:
            source = OaiSource(url=url, name=name, prefix=prefix,
                    last_update=last_update, day_granularity=day_granularity,
                    get_method=get_method)
            source.save()
        except IntegrityError as e:
            return str(e)
    except BadVerbError as e:
        # It is likely that the source only supports GET parameters
        if not get_method:
            addSourceFromURL(url, prefix, True)
        else:
            return unicode(e)
    except (ErrorBase, URLError, HTTPError) as e:
        return unicode(e)
    except XMLSyntaxError as e:
        return 'XML syntax error: '+unicode(e)
        

def recoverWithToken(source, format, token):
    client = source.getClient()
    client._metadata_registry.registerReader(format.name, oai_dc_reader)
    listRecords = client.listRecords(metadataPrefix=format.name, resumptionToken=token)
    saveRecordList(source, format, listRecords)

def saveRecordList(source, format, listRecords):
    def commit_records(buf):
        # First separate existing and new records
        identifiers = [r.identifier for r in buf]
        records_to_update = OaiRecord.objects.filter(identifier__in=identifiers)
        identifiers_found = set([r.identifier for r in records_to_update])
        records_to_create = []
        for r in buf:
            if r.identifier not in identifiers_found:
                records_to_create.append(r)

        # Update existing ones
        if records_to_update:
            bulk_update(records_to_update)

        # Create new records
        OaiRecord.objects.bulk_create(records_to_create)

    buf = []
    for record in listRecords:
        buf.append(create_record_instance(source, record, format))
        if len(buf) >= NB_RECORDS_BEFORE_COMMIT:
            commit_records(buf)
            buf = []
    if len(buf):
        commit_records(buf)

@task(serializer='json',bind=True)
def fetch_from_source_task(self, pk):
    fetch_from_source(pk)

def fetch_from_source(pk):#self, pk):
    #self.update_state(state='PROGRESS')

    source = OaiSource.objects.get(pk=pk)
    baseStatus = 'records'

    # Set up the OAI fetcher
    format, created = OaiFormat.objects.get_or_create(name=METADATA_FORMAT) # defined in oai.settings
    client = source.getClient()
    client._metadata_registry.registerReader('oai_dc', oai_dc_reader)
    client._metadata_registry.registerReader('base_dc', base_dc_reader)

    # Limit queries to records in a time range of 7 days (by default)
    time_chunk = QUERY_TIME_RANGE

    start_date = make_naive(source.last_update, UTC())
    current_date = make_naive(now(), UTC())
    until_date = start_date + time_chunk

    # Restrict to a set ?
    restrict_set = source.restrict_set
    if not restrict_set:
        restrict_set = None

    while start_date <= current_date:
        source.status = baseStatus+' between '+str(start_date)+' and '+str(until_date)
        source.save()

        real_until_date = until_date
        if source.day_granularity and until_date < (current_date - timedelta(days=1)):
            real_until_date -= timedelta(days=1)
        try:
            if restrict_set:
                listRecords = client.listRecords(
                        metadataPrefix=format.name,
                        from_=start_date,
                        until=real_until_date,
                        set=restrict_set)
            else:
                listRecords = client.listRecords(
                        metadataPrefix=format.name,
                        from_=start_date,
                        until=real_until_date)
        except NoRecordsMatchError:
            listRecords = []

        saveRecordList(source, format, listRecords)

        source.last_update = make_aware(min(until_date, current_date), UTC())
        source.save()
        until_date += time_chunk
        start_date += time_chunk

@task(serializer='json',bind=True)
def fetch_sets_from_source(self, pk):
    self.update_state(state='PROGRESS')

    source = OaiSource.objects.get(pk=pk)
    baseStatus = 'sets'

    client = source.getClient()
    
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

    client = source.getClient()
    
    listFormats = client.listMetadataFormats()
    for format in listFormats:
        f, created = OaiFormat.objects.get_or_create(name=format[0])
        f.schema=format[1]
        f.namespace=format[2]
        f.save()

def create_record_instance(source, record, format):
    fullXML = record[1].element()
    metadataStr = etree.tostring(fullXML, pretty_print=True)
    identifier = record[0].identifier()[:256]
    timestamp = record[0].datestamp()
    timestamp = make_aware(timestamp, UTC())

    fingerprint = compute_fingerprint(fullXML, format.name)
    doi = extract_doi(fullXML, format.name)

    return OaiRecord(
        identifier=identifier,
        format=format,
        source=source,
        metadata=metadataStr,
        timestamp=timestamp,
        fingerprint=fingerprint,
        doi=doi)


@transaction.atomic
def update_record(source, record, format):
    if not record[1]:
        return
    modelrecord = create_model_record(source, record, format)
    fullXML = record[1].element()
    metadataStr = etree.tostring(fullXML, pretty_print=True)
    identifier = record[0].identifier()
    timestamp = record[0].datestamp()
    timestamp = make_aware(timestamp, UTC())

    fingerprint = compute_fingerprint(fullXML)
    doi = extract_doi(fullXML)

    modelrecord, created = OaiRecord.objects.get_or_create(
            identifier=identifier,
            format=format,
            defaults={
                'source':source,
                'metadata':metadataStr,
                'timestamp':timestamp,
                'fingerprint':fingerprint,
                'doi':doi})
    if not created:
        modelrecord.timestamp = timestamp
        modelrecord.metadata = metadataStr
        modelrecord.save()

    # Add regular sets
    for s in record[0].setSpec():
        modelset, created = OaiSet.objects.get_or_create(source=source, name=s)
        modelrecord.sets.add(modelset)

    # Apply virtual set extractors
    for extractor in REGISTERED_EXTRACTORS:
        if extractor.format() == format.name:
            sets = extractor.getVirtualSets(fullXML, source)
            # print "Sets for "+identifier+": "+str(sets)
            for set in sets:
                if not set:
                    continue
                name = extractor.subset()+':'+set
                modelset, created = OaiSet.objects.get_or_create(name=name)
                modelrecord.sets.add(modelset)
            sets = None

def rerun_extractor(modelrecord, extractor, deletePrevious=True):
    """
    Reruns an extractor on an existing OaiRecord
    deletePrevious indicates the previous virtual sets created by this extractor
    should be deleted.
    """
    format = modelrecord.format.name
    if format != extractor.format():
        raise ValueError('The metadata formats do not match!')
    fullXML = etree.fromstring(modelrecord.metadata)
    
    if deletePrevious:
        modelrecord.sets.filter(name__startswith=extractor.subset()+':').clear()
    sets = extractor.getVirtualSets(fullXML, modelrecord.source)
    for set in sets:
        if not set:
            continue
        name = extractor.subset()+':'+set
        modelset, created = OaiSet.objects.get_or_create(name=name)
        modelrecord.sets.add(modelset)

@shared_task
def cleanup_resumption_tokens():
    threshold = now() - RESUMPTION_TOKEN_VALIDITY
    ResumptionToken.objects.filter(date_created__lt=threshold).delete()



