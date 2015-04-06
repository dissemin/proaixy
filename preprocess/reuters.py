# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from preprocess.ldacontext import *
from nltk.corpus import reuters
#from nltk.corpus.reader import PlaintextCorpusReader
#reuters = PlaintextCorpusReader('reuters', '(training|test).*')



class ReutersLDAContext(LDAContext):
    def read(self):
        fileids = list(reuters.fileids())
        for fileid in fileids:
            words_view = reuters.words(fileid)
            words = list(words_view)
            words_view.close()
            cat_view = reuters.categories(fileid)
            cat = list(cat_view)
            self.add_document(words, cat, fileid)

