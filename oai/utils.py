# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

class KeyValuePair(object):
    def __init__(self, key, val):
        self.key = key
        self.val = val

def to_kv_pairs(dct):
    for k in dct:
        yield KeyValuePair(k, dct[k])


