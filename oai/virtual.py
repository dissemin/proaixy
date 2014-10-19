# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from lxml import etree
import unicodedata
import re

class VirtualSetExtractor:
    def format():
        """
        Returns the metadata format for which
        the extractor works
        """

    def getVirtualSets(xmlTree):
        """
        Returns the virtual sets for that particular metadata,
        or None is an error occurred.
        """

    def subset():
        """
        Returns the type of virtual sets extracted
        """


class OAIDCAuthorExtractor(VirtualSetExtractor):
    @staticmethod
    def format():
        return 'oai_dc'

    @staticmethod
    def subset():
        return 'author'

    separator_re = re.compile(r',+ *')
    nontext_re = re.compile(r'[^ a-z_]+')

    @staticmethod
    def getVirtualSets(element):
        namespaces = {
         'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
         'dc' : 'http://purl.org/dc/elements/1.1/'}

        xpath_ev = etree.XPathEvaluator(element, namespaces=namespaces)
        matches = xpath_ev.evaluate('oai_dc:dc/dc:creator/text()')
        result = []
        for v in matches:
            name = unicodedata.normalize('NFKD',unicode(v)).encode('ASCII', 'ignore').lower()
            name = name.strip()
            name = OAIDCAuthorExtractor.separator_re.sub('_',name)
            name = OAIDCAuthorExtractor.nontext_re.sub('-',name)
            result.append(name)
        return result

