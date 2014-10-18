# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.timezone import make_naive, UTC

register = template.Library()

@register.filter(is_safe=True)
def isoformat(date):
    return mark_safe(make_naive(date, UTC()).replace(microsecond=0).isoformat()+'Z')

