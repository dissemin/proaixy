from django.contrib import admin
from oai.models import *

class OaiErrorInline(admin.TabularInline):
    model = OaiError
    extra = 0

# class OaiSetSpecInline(admin.TabularInline):
#    model = OaiSetSpec
#    extra = 0
#    raw_id_fields = ('container',)

class OaiSourceAdmin(admin.ModelAdmin):
    inlines = [OaiErrorInline]

#class OaiRecordAdmin(admin.ModelAdmin):
#    inlines = [OaiSetSpecInline]

admin.site.register(OaiSource, OaiSourceAdmin)
admin.site.register(OaiRecord)
admin.site.register(OaiSet)

