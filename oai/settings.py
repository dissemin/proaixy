# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from datetime import timedelta
from oai.virtual import *

# Client settings
query_time_range = timedelta(days=7) # range of initial OAI queries
# This guarantees that if something goes wrong in the middle of
# the harvesting, we still know that we have successfully
# harvested records up to source.last_update, which is
# at most query_time_range behind the record that caused the failure.

# Endpoint settings
repository_name = 'proaixy'
admin_email = 'antonin@delpeuch.eu'
oai_endpoint_name = 'oai'
results_limit = 100
resumption_token_validity = timedelta(hours=6)
metadata_format = 'oai_dc'
own_set_prefix = 'proaixy'

extractors = [OAIDCAuthorExtractor]

# backend settings
NB_RECORDS_BEFORE_COMMIT = 100 # size of the oai record batches between commits

