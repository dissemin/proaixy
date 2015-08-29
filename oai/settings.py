# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from datetime import timedelta

# Client settings
QUERY_TIME_RANGE = timedelta(days=7) # range of initial OAI queries
# This guarantees that if something goes wrong in the middle of
# the harvesting, we still know that we have successfully
# harvested records up to source.last_update, which is
# at most query_time_range behind the record that caused the failure.

# Endpoint settings
REPOSITORY_NAME = 'proaixy'
ADMIN_EMAIL = 'antonin@delpeuch.eu'
OAI_ENDPOINT_NAME = 'oai'
RESULTS_LIMIT = 100
RESUMPTION_TOKEN_VALIDITY = timedelta(hours=6)
METADATA_FORMAT = 'oai_dc'
OWN_SET_PREFIX = 'proaixy'
RESUMPTION_TOKEN_SALT = 'change_me' # salt used to generate resumption tokens


# backend settings
NB_RECORDS_BEFORE_COMMIT = 20 # size of the oai record batches between commits
SLEEP_TIME_BETWEEN_RECORDS = 0.01 # seconds
