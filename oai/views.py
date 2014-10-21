# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.views import generic
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect

from oaipmh.datestamp import tolerant_datestamp_to_datetime
from oaipmh.error import DatestampError

from celery.task.control import revoke

from datetime import datetime

from oai.tasks import *
from oai.models import *
from oai.utils import to_kv_pairs, OaiRequestError
from oai.settings import *
from oai.resumption import *
from oai.forms import *

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def controlPannel(request):
    context = { 'sources': OaiSource.objects.all(),
            'records': OaiRecord.objects.all(),
            'formats': OaiRecord.objects.all(),
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
            source.harvester = fetch_from_source.delay(source.pk)
            source.status = 'records'
            source.save()
            return HttpResponseRedirect('/')
    elif 'set' in request.GET:
        source = get_object_or_404(OaiSource, pk=request.GET.get('set'))
        if not source.harvesting():
            source.harvester = fetch_sets_from_source.delay(source.pk)
            source.status = 'sets'
            source.save()
            return HttpResponseRedirect('/')
    elif 'revoke' in request.GET:
        id = request.GET.get('revoke')
        task = get_object_or_404(TaskMeta, task_id=id)
        revoke(id, terminate=True)
        return HttpResponseRedirect('/')

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

def endpoint(request):
    verb = request.GET.get('verb')
    thisUrl = 'http://'+request.get_host()+request.get_full_path()
    timestamp = datetime.utcnow()
    timestamp = timestamp.replace(microsecond=0)
    context = {'thisUrl':thisUrl,
               'timestamp': timestamp.isoformat()+'Z'}
    if not verb:
        return formatError('badVerb','No verb specified!', context, request)

    params = request.GET
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
    context['baseURL'] = 'http://'+request.get_host()+'/'+oai_endpoint_name
    context['repoName'] = repository_name
    context['adminEmail'] = admin_email
    earliest = OaiRecord.objects.order_by('timestamp').first()
    if earliest:
        context['earliestDatestamp'] = earliest.timestamp
    else:
        context['earliestDatestamp'] = timezone.now()
    return render(request, 'oai/identify.xml', context, content_type='text/xml')

def getRecord(request, context):
    format_name = request.GET.get('metadataPrefix')
    try:
        format = OaiFormat.objects.get(name=format_name)
    except ObjectDoesNotExist:
        raise OaiRequestError('badArgument', 'The metadata format "'+format_name+'" does not exist.')
    record_id = request.GET.get('identifier')
    try:
        record = OaiRecord.objects.get(identifier=record_id)
    except ObjectDoesNotExist:
        raise OaiRequestError('badArgument', 'The record "'+record_id+'" does not exist.')
    context['record'] = record
    return render(request, 'oai/GetRecord.xml', context, content_type='text/xml')

def listSomething(request, context, verb):
    if 'resumptionToken' in request.GET:
        return resumeRequest(context, request, verb, request.GET.get('resumptionToken'))
    queryParameters = dict()
    error = None
    if verb == 'ListRecords' or verb == 'ListIdentifiers':
        queryParameters = getListQuery(context, request)
    return handleListQuery(request, context, verb, queryParameters)

def listMetadataFormats(request, context):
    queryParameters = dict()
    matches = OaiFormat.objects.all()
    if 'identifier' in request.GET:
        id = request.GET.get('identifier')
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

    # Validate arguments
    getParams = request.GET.dict()
    
    # metadataPrefix
    metadataPrefix = getParams.pop('metadataPrefix', None)
    if not metadataPrefix:
        raise OaiRequestError('badArgument', 'The metadataPrefix argument is required.')
    try:
        format = OaiFormat.objects.get(name=metadataPrefix)
    except ObjectDoesNotExist:
        raise OaiRequestError('badArgument', 'The metadata format "'+metadataPrefix+'" does not exist.')
    queryParameters['format'] = format

    # set
    set = getParams.pop('set', None)
    if set:
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
        queryParameters['timestamp__gte'] = make_aware(from_, UTC())

    # until
    until = getParams.pop('until', None)
    if until:
        try:
            until = tolerant_datestamp_to_datetime(until)
        except DatestampError:
            raise OaiRequestError('badArgument',
                    'The parameter "until" expects a valid date, not "'+until+"'.")
        queryParameters['timestamp__lte'] = make_aware(until, UTC())

    # Check that from <= until
    if from_ and until and from_ > until:
        raise OaiRequestError('badArgument', '"from" should not be after "until".')

    # Check that there are no other arguments
    getParams.pop('verb', None)
    for key in getParams:
        raise OaiRequestError('badArgument', 'The argument "'+key+'" is illegal.')

    return queryParameters
 



