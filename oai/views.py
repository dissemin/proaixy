# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.views import generic
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from oaipmh.datestamp import tolerant_datestamp_to_datetime
from oaipmh.error import DatestampError

from datetime import datetime

from oai.tasks import *
from oai.models import *
from oai.utils import to_kv_pairs
from oai.settings import *
from oai.resumption import *

def updateSource(request, pk):
    source = get_object_or_404(OaiSource, pk=pk)
    fetch_from_source.apply_async(eta=timezone.now(), kwargs={'pk':pk})
    return render(request, 'oai/updateSource.html', {'source':source})

def updateSets(request, pk):
    source = get_object_or_404(OaiSource, pk=pk)
    fetch_sets_from_source.apply_async(eta=timezone.now(), kwargs={'pk':pk})
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

    if verb == 'Identify':
        return identify(request, context)
    elif verb == 'ListRecords' or verb == 'ListIdentifiers' or verb == 'ListSets':
        if 'resumptionToken' in request.GET:
            return resumeRequest(context, request, verb, request.GET.get('resumptionToken'))
        queryParameters = dict()
        error = None
        if verb == 'ListRecords' or verb == 'ListIdentifiers':
            queryParameters, error = getListQuery(context, request)
        if error:
            return error
        return handleListQuery(request, context, verb, queryParameters)
    else:
        return formatError('badVerb','Verb "'+verb+'" is not implemented.', context, request)

def identify(request, context):
    context['baseURL'] = 'http://'+request.get_host()+'/'+oai_endpoint_name
    earliest = OaiRecord.objects.order_by('timestamp').first()
    if earliest:
        context['earliestDatestamp'] = timezone.make_naive(earliest.timestamp, timezone.UTC())
    else:
        context['earliestDatestamp'] = '1990-01-01'
    return render(request, 'oai/identify.xml', context, content_type='text/xml')

def getListQuery(context, request):
    """
    Returns two objects:
    - the query dictionary corresponding to the request or None if anything went wrong
    - the error page to return if anything went wrong, or None otherwise
    """
    queryParameters = dict()

    # Validate arguments
    getParams = request.GET.dict()
    
    # metadataPrefix
    metadataPrefix = getParams.pop('metadataPrefix', None)
    if not metadataPrefix:
        return None, formatError('badArgument', 'The metadataPrefix argument is required.', context, request)
    # TODO check that the syntax of the format is correct
    queryParameters['format'] = metadataPrefix

    # set
    set = getParams.pop('set', None)
    if set:
        # TODO check that the syntax of the set is correct
        matchingSet = OaiSet.byRepresentation(set)
        if not matchingSet:
            return None, formatError('badArgument', 'The set "'+set+'" does not exist.', context, request)
        queryParameters['sets'] = matchingSet
    
    # from
    from_ = getParams.pop('from', None)
    if from_:
        try:
            from_ = tolerant_datestamp_to_datetime(from_)
        except DatestampError:
            return None, formatError('badArgument', 'The parameter "from" expects a valid date, not "'+from_+"'.", context, request)
        queryParameters['timestamp__gte'] = make_aware(from_, UTC())

    # until
    until = getParams.pop('until', None)
    if until:
        try:
            until = tolerant_datestamp_to_datetime(until)
        except DatestampError:
            return None, formatError('badArgument', 'The parameter "until" expects a valid date, not "'+until+"'.", context, request)
        queryParameters['timestamp__lte'] = make_aware(until, UTC())

    # Check that from <= until
    if from_ and until and from_ > until:
        return None, formatError('badArgument', '"from" should not be after "until".', context, request)

    # Check that there are no other arguments
    getParams.pop('verb', None)
    for key in getParams:
        return None, formatError('badArgument', 'The argument "'+key+'" is illegal.', context, request)

    return queryParameters, None
 



