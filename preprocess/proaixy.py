# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from preprocess.ldacontext import *
from lxml import etree

from oai.models import *

class ProaixyLDAContext(LDAContext):
    def read(self, queryset):
        namespaces = {
                'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
                'dc': 'http://purl.org/dc/elements/1.1/'}
        for record in queryset:
            root = etree.parse(record.metadata)
            xpath_ev = etree.XPathEvaluator(root, namespaces=namespaces)

            topics = []
            topic_elems = xpath_ev.evaluate('oai_dc:dc/dc:subject/text()')
            for t in topic_elems:
                topic = v.text

            abstract_elems = xpath_ev.evaluate("oai_dc:dc/dc:description/text()")
            cur_abstract = ""
            for node in abstract_elems:
                if len(cur_abstract) < len(node.text):
                    cur_abstract = node.text
            
            abstract = self.tokenize_abstract(cur_abstract)
            print "add document "+str(abstract)[:50]+"\ntopics: "+str(topics)[:40]+"\nid: "+str(record.identifier)            
            self.add_document(abstract, topics, record.identifier)

