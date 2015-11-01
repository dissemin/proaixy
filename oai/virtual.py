# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from lxml import etree
from lxml import html
from unidecode import unidecode
import name_tools
import HTMLParser
import re

from oai.models import OaiSource
from oai.utils import tolerant_datestamp_to_datetime, create_paper_fingerprint, parse_comma_name
from oai.name import *

doi_re = re.compile(r'^ *(?:[Dd][Oo][Ii] *[:=])? *(?:http://dx\.doi\.org/)?(10\.[0-9]{4,}[^ ]*/[^ ]+) *$')

def to_doi(candidate):
    """ Convert a representation of a DOI to its normal form. """
    m = doi_re.match(candidate)
    if m:
        return m.groups()[0]
    else:
        return None

oai_dc_namespaces = {
     'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
     'dc' : 'http://purl.org/dc/elements/1.1/'}

base_dc_namespaces = {
    'base_dc': 'http://oai.base-search.net/base_dc/',
    'dc': 'http://purl.org/dc/elements/1.1/'}

def extract_doi(element, schema='oai_dc'):
    if schema == 'oai_dc':
        identifier_field = 'oai_dc:dc/dc:identifier/text()'
        namespaces = oai_dc_namespaces
    elif schema == 'base_dc':
        identifier_field = 'base_dc:dc/dc:identifier/text()'
        namespaces = base_dc_namespaces
    else:
        raise ValueError("Invalid schema")

    xpath_ev = etree.XPathEvaluator(element, namespaces=namespaces)
    matches = xpath_ev.evaluate(identifier_field)
    for v in matches:
        doi = to_doi(v.strip())
        if doi is not None:
            return doi

def compute_fingerprint(element, schema='oai_dc'):
    if schema == 'oai_dc':
        author_field = 'oai_dc:dc/dc:creator/text()'
        title_field = 'oai_dc:dc/dc:title/text()'
        date_field = 'oai_dc:dc/dc:date/text()'
        namespaces = oai_dc_namespaces
    elif schema == 'base_dc':
        author_field = 'base_dc:dc/dc:creator/text()'
        title_field = 'base_dc:dc/dc:title/text()'
        date_field = 'base_dc:dc/base_dc:year/text()'
        namespaces = base_dc_namespaces
    else:
        raise ValueError("Invalid schema")

    xpath_ev = etree.XPathEvaluator(element, namespaces=namespaces)

    # Compute authors
    authors = []
    matches = xpath_ev.evaluate(author_field)
    for v in matches:
        if v.strip() == "":
            continue
        name = unicode(html.fromstring(v).text)
        authors.append(parse_comma_name(name))
    if not authors:
        return

    # Title
    title = None
    matches = xpath_ev.evaluate(title_field)
    for v in matches:
        v = v.strip()
        if not v:
            continue
        title = v
        break

    # Year
    date = None
    matches = xpath_ev.evaluate(date_field)
    for v in matches:
        try:
            parsed = tolerant_datestamp_to_datetime(v)
            if date is None or parsed < date:
                date = parsed
        except ValueError:
            continue

    if date and title:
        return create_paper_fingerprint(title, authors, date.year)

class VirtualSetExtractor:
    def formats():
        """
        Returns the metadata formats for which
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
    def formats():
        return ['oai_dc','base_dc']

    @staticmethod
    def subset():
        return 'source'

    @staticmethod
    def getVirtualSets(element, source):
        return [source.prefix]


class OAIDCAuthorExtractor(VirtualSetExtractor):
    @staticmethod
    def formats():
        return ['oai_dc','base_dc']

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
    def formats():
        return ['oai_dc','base_dc']

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
    def formats():
        return ['oai_dc','base_dc']

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

