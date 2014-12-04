from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()
admin.site.site_header = 'Proaixy administration'

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('oai.urls')),
)
