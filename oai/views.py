# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from django.db.models import Sum

from oaipmh.datestamp import tolerant_datestamp_to_datetime
from oaipmh.error import DatestampError

from celery.task.control import revoke

from datetime import datetime

import requests

from oai.tasks import *
from oai.models import *
from oai.utils import *
from oai.name import parse_comma_name
from oai.settings import *
from oai.resumption import *
from oai.forms import *

def is_admin(user):
    return user.is_superuser

PRODUCTION_ROOT_URL = "/~pintoch/proaixy/"

@user_passes_test(is_admin)
def controlPannel(request):
    context = { 'sources': OaiSource.objects.extra(order_by = ['name']),
            'nbRecords': OaiSource.objects.all().aggregate(Sum('nb_records'))['nb_records__sum'],
            'records': OaiRecord.objects.all(),
            'addSourceForm': AddSourceForm() }

    if request.method == 'POST':
        form = AddSourceForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            prefix = form.cleaned_data['prefix']
            errorMsg = addSourceFromURL(url, prefix)
            if errorMsg:
                context['errorMsg'] = errorMsg
        else:
            context['errorMsg'] = 'Invalid URL.'
    elif 'harvest' in request.GET:
        source = get_object_or_404(OaiSource, pk=request.GET.get('harvest'))
        if not source.harvesting():
            source.harvester = fetch_from_source_task.delay(source.pk)
            source.status = 'records'
            source.save()
            return HttpResponseRedirect(PRODUCTION_ROOT_URL)
    elif 'set' in request.GET:
        source = get_object_or_404(OaiSource, pk=request.GET.get('set'))
        if not source.harvesting():
            source.harvester = fetch_sets_from_source.delay(source.pk)
            source.status = 'sets'
            source.save()
            return HttpResponseRedirect(PRODUCTION_ROOT_URL)
    elif 'revoke' in request.GET:
        id = request.GET.get('revoke')
        task = get_object_or_404(TaskMeta, task_id=id)
        revoke(id, terminate=True)
        return HttpResponseRedirect(PRODUCTION_ROOT_URL)

    return render(request, 'oai/controlPannel.html', context)

@user_passes_test(is_admin)
def updateFormats(request, pk):
    source = get_object_or_404(OaiSource, pk=pk)
    fetch_formats_from_source.apply_async(eta=timezone.now(), kwargs={'pk':pk})
    return render(request, 'oai/updateSource.html', {'source':source})

def formatError(errorCode, errorMessage, context, request):
    context['errorCode'] = errorCode
    context['errorMessage'] = errorMessage
    return render(request, 'oai/error.xml', context, content_type='text/xml')

@csrf_exempt
def endpoint(request):
    params = dict(request.POST.items() + request.GET.items())
    verb = params.get('verb')

    thisUrl = 'http://'+request.get_host()+request.get_full_path()
    timestamp = datetime.utcnow()
    timestamp = timestamp.replace(microsecond=0)
    context = {'thisUrl':thisUrl,
               'timestamp': timestamp.isoformat()+'Z'}

    if not verb:
        return formatError('badVerb','No verb specified!', context, request)

    context['params'] = to_kv_pairs(params)

    try:
        if verb == 'Identify':
            return identify(request, context)
        elif verb == 'GetRecord':
            return getRecord(request, context)
        elif verb == 'ListRecords' or verb == 'ListIdentifiers' or verb == 'ListSets':
            return listSomething(request, context, verb)
        elif verb == 'ListMetadataFormats':
            return listMetadataFormats(request, context)
        else:
            raise OaiRequestError('badVerb', 'Verb "'+verb+'" is not implemented.')
    except OaiRequestError as e:
        return formatError(e.code, e.reason, context, request)

def identify(request, context):
    context['baseURL'] = 'http://'+request.get_host()+'/'+OAI_ENDPOINT_NAME
    context['repoName'] = REPOSITORY_NAME
    context['adminEmail'] = ADMIN_EMAIL
    earliest = OaiRecord.objects.order_by('last_modified').first()
    if earliest:
        context['earliestDatestamp'] = earliest.timestamp
    else:
        context['earliestDatestamp'] = timezone.now()
    return render(request, 'oai/identify.xml', context, content_type='text/xml')

def getRecord(request, context):
    getpost = request.GET.dict()
    getpost.update(request.POST.dict())
    format_name = getpost.get('metadataPrefix')
    try:
        format = OaiFormat.objects.get(name=format_name)
    except ObjectDoesNotExist:
        raise OaiRequestError('badArgument', 'The metadata format "'+format_name+'" does not exist.')
    record_id = getpost.get('identifier')
    try:
        record = OaiRecord.objects.get(identifier=record_id)
    except ObjectDoesNotExist:
        raise OaiRequestError('badArgument', 'The record "'+record_id+'" does not exist.')
    context['record'] = record
    return render(request, 'oai/GetRecord.xml', context, content_type='text/xml')

def listSomething(request, context, verb):
    getpost = request.GET.dict()
    getpost.update(request.POST.dict())
    context['format'] = getpost.get('metadataPrefix')
    if 'resumptionToken' in getpost:
        return resumeRequest(context, request, verb, getpost.get('resumptionToken'))
    queryParameters = dict()
    error = None
    if verb == 'ListRecords' or verb == 'ListIdentifiers':
        queryParameters = getListQuery(context, request)
    return handleListQuery(request, context, verb, queryParameters)

def listMetadataFormats(request, context):
    getpost = request.GET.dict()
    getpost.update(request.POST.dict())
    queryParameters = dict()
    matches = OaiFormat.objects.all()
    if 'identifier' in getpost:
        id = getpost.get('identifier')
        records = OaiRecord.objects.filter(identifier=id)
        if records.count() == 0:
            raise OaiRequestError('badArgument', 'This identifier "'+id+'" does not exist.')
        context['records'] = records
        return render(request, 'oai/ListFormatsByIdentifier.xml', context, content_type='text/xml')
    else:
        context['matches'] = matches
        return render(request, 'oai/ListMetadataFormats.xml', context, content_type='text/xml')


def getListQuery(context, request):
    """
    Returns the query dictionary corresponding to the request
    Raises OaiRequestError if anything goes wrong
    """
    queryParameters = dict()

    # Both POST and GET arguments *must* be supported according to the standard
    # In this implementation, POST arguments are prioritary.
    getParams = dict(request.GET.dict().items() + request.POST.dict().items())
    
    # metadataPrefix
    metadataPrefix = getParams.pop('metadataPrefix', None)
    if not metadataPrefix:
        raise OaiRequestError('badArgument', 'The metadataPrefix argument is required.')
    if metadataPrefix != 'any':
        try:
            format = OaiFormat.objects.get(name=metadataPrefix)
        except ObjectDoesNotExist:
            raise OaiRequestError('badArgument', 'The metadata format "'+metadataPrefix+'" does not exist.')
        queryParameters['format'] = format

    # set
    set = getParams.pop('set', None)
    if set:
        if set.startswith(FINGERPRINT_IDENTIFIER_PREFIX):
            fingerprint = set[len(FINGERPRINT_IDENTIFIER_PREFIX):]
            if not fingerprint:
                raise OaiRequestError('badArgument', 'Invalid fingerprint.')
            queryParameters['fingerprint'] = fingerprint
        elif set.startswith(DOI_IDENTIFIER_PREFIX):
            doi = set[len(DOI_IDENTIFIER_PREFIX):]
            if not doi:
                raise OaiRequestError('badArgument', 'Invalid DOI.')
            queryParameters['doi'] = doi.lower()
        else:
            matchingSet = OaiSet.byRepresentation(set)
            if not matchingSet:
                raise OaiRequestError('badArgument', 'The set "'+set+'" does not exist.')
            queryParameters['sets'] = matchingSet

    
    # from
    from_ = getParams.pop('from', None)
    if from_:
        try:
            from_ = tolerant_datestamp_to_datetime(from_)
        except DatestampError:
            raise OaiRequestError('badArgument',
                    'The parameter "from" expects a valid date, not "'+from_+"'.")
        queryParameters['last_modified__gte'] = make_aware(from_, UTC())

    # until
    until = getParams.pop('until', None)
    if until:
        try:
            until = tolerant_datestamp_to_datetime(until)
        except DatestampError:
            raise OaiRequestError('badArgument',
                    'The parameter "until" expects a valid date, not "'+until+"'.")
        queryParameters['last_modified__lte'] = make_aware(until, UTC())

    # Check that from <= until
    if from_ and until and from_ > until:
        raise OaiRequestError('badArgument', '"from" should not be after "until".')

    # Check that there are no other arguments
    getParams.pop('verb', None)
    for key in getParams:
        raise OaiRequestError('badArgument', 'The argument "'+key+'" is illegal.')

    return queryParameters
 

oai_dc_namespaces = {'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
 'dc': 'http://purl.org/dc/elements/1.1/'}
base_dc_namespaces = {'base_dc': 'http://oai.base-search.net/base_dc/',
 'dc': 'http://purl.org/dc/elements/1.1/'}

def get_pdf_url(record):
    xml = etree.fromstring(record.metadata)
    oa = False
    identifier_field = 'oai_dc:dc/dc:identifier/text()'
    link_field = 'oai_dc:dc/dc:link/text()'
    if record.format_id == 1:
        identifier_field = 'base_dc:dc/base_dc:identifier/text()'
        link_field = 'base_dc:dc/base_dc:link/text()'
        xpath_ev = etree.XPathEvaluator(xml, namespaces=base_dc_namespaces)
        oa_status = xpath_ev.evaluate('base_dc:dc/base_dc:oa/text()')
        for matches in oa_status:
            if matches.strip() == '1':
                oa = True

    else:
        xpath_ev = etree.XPathEvaluator(xml, namespaces=oai_dc_namespaces)
    print record.format_id
    matches = xpath_ev.evaluate(identifier_field)
    matches += xpath_ev.evaluate(link_field)
    for m in matches:
        print m
        if oa or m.endswith('.pdf'):
            return m

def get_doi(request, doi):
    doi_url = 'http://dx.doi.org/' + doi
    rg_pdf_url = None
    for r in OaiRecord.objects.filter(doi=doi):
        print r.identifier
        pdf_url = get_pdf_url(r)
        if pdf_url:
            if 'researchgate.net' in pdf_url:
                rg_pdf_url = pdf_url
            else:
                return HttpResponseRedirect(pdf_url)

    r = requests.get('http://doi-cache.dissem.in/' + doi)
    fp = get_fingerprint_from_citeproc(r.json())
    if fp:
        for r in OaiRecord.objects.filter(fingerprint=fp):
            print r.identifier
            pdf_url = get_pdf_url(r)
            if pdf_url:
                return HttpResponseRedirect(pdf_url)

    if rg_pdf_url:
        return HttpResponseRedirect(rg_pdf_url)
    return HttpResponseRedirect(doi_url)

