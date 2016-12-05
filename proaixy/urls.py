from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.conf import settings

admin.autodiscover()
admin.site.site_header = 'Proaixy administration'

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('oai.urls')),
]

if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
