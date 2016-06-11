# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.template import RequestContext, loader
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from oaipmh.datestamp import tolerant_datestamp_to_datetime
from oaipmh.error import DatestampError

from datetime import datetime

from oai.tasks import *
from oai.models import *
from oai.utils import to_kv_pairs, OaiRequestError
from oai.settings import *

def handleListQuery(request, context, queryType, parameters, firstpk=None, first_timestamp=None):
    if queryType == 'ListRecords' or queryType == 'ListIdentifiers':
        matches = OaiRecord.objects.order_by('last_modified', 'pk').filter(**parameters)
    elif queryType == 'ListSets':
        matches = OaiSet.objects.order_by('pk')
    else:
        raise OaiRequestError('badArgument', 'Illegal verb.')
    if queryType == 'ListRecords' and firstpk is not None and first_timestamp is not None:
        matches = matches.filter(pk__gte=firstpk,last_modified__gte=first_timestamp)
    matches = list(matches[:RESULTS_LIMIT+1])
    count = len(matches)
    # Should we create a resumption token?
    if count > RESULTS_LIMIT:
        lastpk = matches[-1].pk
        last_timestamp = matches[-1].last_modified
        token = createResumptionToken(queryType, parameters, lastpk, last_timestamp)
        context['token'] = token
    context['matches'] = matches
    return render(request, 'oai/'+queryType+'.xml', context, content_type='text/xml')


def createResumptionToken(queryType, queryParameters, firstpk, first_timestamp):
    token = ResumptionToken(queryType=queryType,
            firstpk=firstpk, first_timestamp=first_timestamp)
    if 'format' in queryParameters:
        token.metadataPrefix = queryParameters['format']
    if 'last_modified__gte' in queryParameters:
        token.fro = queryParameters['last_modified__gte']
    if 'last_modified__lte' in queryParameters:
        token.until = queryParameters['last_modified__lte']
    if 'sets' in queryParameters:
        token.set = queryParameters['sets']
    token.save()
    token.genkey()
    return token

def resumeRequest(context, request, queryType, key):
    try:
        token = ResumptionToken.objects.get(queryType=queryType, key=key)
    except ObjectDoesNotExist:
        raise OaiRequestError('badResumptionToken', 'This resumption token is invalid: "'+key+'", "'+queryType+'"', context, request)
    parameters = dict()
    format = token.metadataPrefix or 'any'
    context['format'] = format
    if format != 'any':
        parameters['format'] = format
    if token.set:
        parameters['sets'] = token.set
    if token.fro:
        parameters['last_modified__gte'] = token.fro
    if token.until:
        parameters['last_modified__lte'] = token.until
    return handleListQuery(request, context, queryType, parameters, token.firstpk, token.first_timestamp)
    


