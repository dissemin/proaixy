from preprocess.reuters import *
from oai.models import *
from preprocess.proaixy import *
import cPickle

def dump(obj, fname):
    cPickle.dump(obj, open(fname, 'wb'))

def load(fname):
    return cPickle.load(open(fname, 'rb'))

LOAD_REUTERS = False
LOAD_PROAIXY = True
threshold = 2

ONLINE_LDA_REUTERS = False
ONLINE_LDA_PROAIXY = True

if LOAD_REUTERS:
    r = ReutersLDAContext()
    r.read()
    r.prune(threshold)
    dump(r, 'models/reuters.pkl')
else:
    r = load('models/reuters.pkl')

if LOAD_PROAIXY:
    p = ProaixyLDAContext()
    queryset = OaiRecord.objects.filter(source_id=2)[:10]
    p.read(queryset)
    p.prune(ld)
    dump(r, 'models/proaixy.pkl')
else:
    p = load('models/proaixy.pkl')

if ONLINE_LDA_REUTERS:
    lda_r = r.perform_onlinelda()
    dump(lda_r, 'models/lda_reuters.pkl')
else:
    lda_r = load('models/lda_reuters.pkl')

if ONLINE_LDA_PROAIXY:
    lda_p = p.perform_onlinelda()
    dump(lda_p, 'models/lda_proaixy.pkl')
else:
    lda_p = load('models/lda_proaixy.pkl')

