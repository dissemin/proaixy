# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

class AddSourceForm(forms.Form):
    url = forms.URLField(label='OAI endpoint', max_length=512)
    prefix = forms.CharField(label='Prefix', max_length=100)


