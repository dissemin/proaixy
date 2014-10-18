# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(is_safe=True)
def isoformat(date):
    return mark_safe(date.replace(microsecond=0).isoformat()+'Z')

