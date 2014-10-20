# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.contrib.auth.views import login

from oai.views import *

urlpatterns = patterns('',
        url(r'^'+oai_endpoint_name+'$', endpoint, name='oaiEndpoint'),
        url(r'^$', controlPannel, name='controlPannel'),
        url(r'^login/$', login, {'template_name': 'admin/login.html'}),
        url(r'^source/(?P<pk>\d+)/update/$', updateSource, name='updateSource'),
        url(r'^source/(?P<pk>\d+)/updatesets/$', updateSets, name='updateSets'),
        url(r'^source/(?P<pk>\d+)/updateformats/$', updateFormats, name='updateFormats')
)
