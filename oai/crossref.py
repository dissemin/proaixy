import requests
import json
from time import sleep
from oaipmh.metadata import MetadataRegistry

class FakeOaiClientForCrossref(object):
    """
    Crossref does not provide a public OAI interface,
    so we use their REST API.
    """

    def __init__(self):
        # not used but kept for uniformity with the rest
        self._metadata_registry = MetadataRegistry()

    def listRecords(self, metadataPrefix='citeproc',
                    from_ = None,
                    until = None,
                    set = None):
        fltr = []
        if from_:
            fltr.append('from-index-date:'+unicode(from_.date().isoformat()))
        if until:
            fltr.append('until-index-date:'+unicode(until.date().isoformat()))
        fltr = ','.join(fltr)

        cursor = '*'
        found = True
        while found:
            found = False
            try:
                sleep(1)
                q = requests.get('http://api.crossref.org/works',
                            params={'cursor':cursor,
                        'filter':fltr,'rows':1000})
                print(q.url)
                q = q.json()
                cursor = q['message']['next-cursor']

                records = []
                for item in q.get('message', {}).get('items', []):
                    found = True
                    yield item
            except (ValueError, KeyError, requests.exceptions.RequestException) as e:
                print(e)
                sleep(30)
                found = True

 
