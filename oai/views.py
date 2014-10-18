from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.views import generic
from django.utils import timezone

from datetime import datetime

from oai.tasks import *
from oai.models import *

oai_endpoint_name = 'oai'

def updateSource(request, pk):
    source = get_object_or_404(OaiSource, pk=pk)
    fetch_from_source.apply_async(eta=timezone.now(), kwargs={'pk':pk})
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
    if verb == 'Identify':
        return identify(request, context)
    elif verb == 'ListRecords':
        return listRecords(request, context)
    else:
        return formatError('badVerb','Bad verb. Verb "'+verb+'" is not implemented.', context, request)

def identify(request, context):
    context['baseURL'] = 'http://'+request.get_host()+'/'+oai_endpoint_name
    earliest = OaiRecord.objects.order_by('timestamp').first()
    if earliest:
        context['earliestDatestamp'] = timezone.make_naive(earliest.timestamp, timezone.UTC())
    else:
        context['earliestDatestamp'] = '1990-01-01'
    return render(request, 'oai/identify.xml', context, content_type='text/xml')

def listRecords(request, context)
    queryParameters = dict()

    # Validate arguments
    
    # metadataPrefix
    metadataPrefix = request.GET.get('metadataPrefix')
    if not metadataPrefix:
        return formatError('badArgument', 'The metadataPrefix argument is required.', context, request)
    # TODO check that the syntax of the format is correct
    queryParameters['format'] = metadataPrefix

    # set
    set = request.GET.get('set')
    if set:
        # TODO check that the syntax of the set is correct
        queryParameters['set'] = set
    
    # from, until, and so on
        
    matches = []
    context['matches'] = matches
    return render(request, 'oai/listRecords.xml', context, content_type='text/xml')

