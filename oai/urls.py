from django.conf.urls import patterns, url

from oai.views import *

urlpatterns = patterns('',
        url(r'^'+oai_endpoint_name+'$', endpoint, name='oaiEndpoint'),
        url(r'^source/(?P<pk>\d+)/update/$', updateSource, name='updateSource')
)
