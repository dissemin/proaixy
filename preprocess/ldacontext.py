# -*- encoding: utf-8 -*-

from __future__ import unicode_literals, print_function

from collections import defaultdict
from random import random
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from online.onlineldavb import *

class LDAContext(object):
    def __init__(self):
        self.vocab = defaultdict(int)
        self.vocab_size = 0
        self.vocfreq = defaultdict(int)
        self.char_re = re.compile('.*[a-zA-Z]')
        self.stop = set(stopwords.words('english')) | set(stopwords.words('french')) | set(['http'])

        self.docid = []
        self.domains = []
        self.tdm = []
        self.words = []

    def not_a_stopword(self, w):
        return (self.char_re.match(w) is not None) and not w.startswith('//') and w not in self.stop

    def tokenize_abstract(self, string):
        words = word_tokenize(string)
        words = map(unicode.lower, words)
        words = filter(self.not_a_stopword, words)
        return words

    def add_document(self, words, topics, docid):
        d = defaultdict(int)
        for tkid in map(self.to_token_id, words):
            d[tkid] += 1

        self.docid.append(docid)
        self.domains.append(topics)
        self.tdm.append(d.items())
        self.words.append(words)

    def to_token_id(self, word):
        if word in self.vocab:
            n = self.vocab[word]
            self.vocfreq[n] += 1
            return n
        self.vocab[word] = self.vocab_size
        self.vocfreq[self.vocab_size] += 1
        self.vocab_size += 1
        return self.vocab_size-1

    def prune(self, cutoff):
        print("Vocab size before pruning: "+str(self.vocab_size))
        for i in range(len(self.tdm)):
            self.tdm[i] = filter(lambda (x,c): c > cutoff, self.tdm[i])

        for x, c in self.vocab.items():
            if c <= cutoff:
                del self.vocab[x]
        self.vocab_size = len(self.vocab)
        print("Vocab size after pruning: "+str(self.vocab_size))

    def perform_onlinelda(self):
        K = 200
        alpha = 0.01
        eta = 0.01
        tau = 256
        kappa = 0.5
        minibatch_size = 1024
        lda = OnlineLDA(self.vocab_size, K, len(self.docid), alpha, eta, tau, kappa)
        
        wordids = []
        wordcts = []
        for i in range(len(self.docid)):
            if len(wordids) == minibatch_size:
                gamma, bound = lda.update_lambda((wordids,wordcts))
                print(str(i)+"\tbound: "+str(bound))
                wordids = []
                wordcts = []
            wordids.append([x[0] for x in self.tdm[i]])
            wordcts.append([x[1] for x in self.tdm[i]])

        if len(wordids):
            lda.update_lambda((wordids,wordcts))
        return lda
            


        


