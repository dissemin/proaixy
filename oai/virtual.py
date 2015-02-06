# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from lxml import etree
from lxml import html
from unidecode import unidecode
import name_tools
import HTMLParser
import re

from oai.models import OaiSource

class VirtualSetExtractor:
    def format():
        """
        Returns the metadata format for which
        the extractor works
        """

    def getVirtualSets(xmlTree, source):
        """
        Returns the virtual sets for that particular metadata,
        fetched from the given source,
        or None is an error occurred.
        """

    def subset():
        """
        Returns the type of virtual sets extracted
        """

class OAIDCSourceExtractor(VirtualSetExtractor):
    @staticmethod
    def format():
        return 'oai_dc'

    @staticmethod
    def subset():
        return 'source'

    @staticmethod
    def getVirtualSets(element, source):
        return [source.prefix]


class OAIDCAuthorExtractor(VirtualSetExtractor):
    @staticmethod
    def format():
        return 'oai_dc'

    @staticmethod
    def subset():
        return 'author'

    separator_re = re.compile(r',+ *')
    escaping_chars_re = re.compile(r'[\{\}\\]')
    nontext_re = re.compile(r'[^a-z_]+')
    final_nontext_re = re.compile(r'[^a-z_]+$')

    @staticmethod
    def getVirtualSets(element, source):
        namespaces = {
         'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
         'dc' : 'http://purl.org/dc/elements/1.1/'}

        xpath_ev = etree.XPathEvaluator(element, namespaces=namespaces)
        matches = xpath_ev.evaluate('oai_dc:dc/dc:creator/text()')
        result = []
        for v in matches:
            if v.strip() == "":
                continue
            name = unicode(html.fromstring(v).text)
            name = unidecode(name).lower()
            name = name.strip()
            name = OAIDCAuthorExtractor.separator_re.sub('_',name)
            name = OAIDCAuthorExtractor.escaping_chars_re.sub('',name)
            name = OAIDCAuthorExtractor.final_nontext_re.sub('',name)
            name = OAIDCAuthorExtractor.nontext_re.sub('-',name)
            result.append(name)
        return result

class OAIDCLastnameExtractor(VirtualSetExtractor):
    @staticmethod
    def format():
        return 'oai_dc'

    @staticmethod
    def subset():
        return 'lastname'

    escaping_chars_re = re.compile(r'[\{\}\\]')
    nontext_re = re.compile(r'[^a-z_]+')
    final_nontext_re = re.compile(r'[^a-z_]+$')

    @staticmethod
    def getVirtualSets(element, source):
        namespaces = {
         'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
         'dc' : 'http://purl.org/dc/elements/1.1/'}

        xpath_ev = etree.XPathEvaluator(element, namespaces=namespaces)
        matches = xpath_ev.evaluate('oai_dc:dc/dc:creator/text()')
        result = []
        for v in matches:
            if v.strip() == "":
                continue
            name = unicode(html.fromstring(v).text)
            name = unidecode(name)
            pre, first, last, post = name_tools.split(name)
            name = last.lower().strip()
            name = OAIDCLastnameExtractor.escaping_chars_re.sub('',name)
            name = OAIDCLastnameExtractor.final_nontext_re.sub('',name)
            name = OAIDCLastnameExtractor.nontext_re.sub('-',name)
            result.append(name)
        return result

class OAIDCAuthorSigExtractor(VirtualSetExtractor):
    @staticmethod
    def format():
        return 'oai_dc'

    @staticmethod
    def subset():
        return 'authorsig'

    escaping_chars_re = re.compile(r'[\{\}\\]')
    nontext_re = re.compile(r'[^a-z_]+')
    final_nontext_re = re.compile(r'[^a-z_]+$')

    @staticmethod
    def getVirtualSets(element, source):
        namespaces = {
         'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
         'dc' : 'http://purl.org/dc/elements/1.1/'}

        xpath_ev = etree.XPathEvaluator(element, namespaces=namespaces)
        matches = xpath_ev.evaluate('oai_dc:dc/dc:creator/text()')
        result = []
        for v in matches:
            if v.strip() == "":
                continue
            name = unicode(html.fromstring(v).text)
            name = unidecode(name)
            pre, first, last, post = name_tools.split(name)
            name = last.lower().strip()
            name = OAIDCAuthorSigExtractor.escaping_chars_re.sub('',name)
            name = OAIDCAuthorSigExtractor.final_nontext_re.sub('',name)
            name = OAIDCAuthorSigExtractor.nontext_re.sub('-',name)
            if len(first):
                result.append(first[0].lower()+'-'+name)
        return result



REGISTERED_EXTRACTORS = [
        OAIDCAuthorSigExtractor,
        OAIDCAuthorExtractor,
        OAIDCSourceExtractor,
        ]

