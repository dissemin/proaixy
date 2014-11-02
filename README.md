Proaixy
=======

A simple OAI proxy adding sets to the records, to enable a "search" by author name for instance.

Proaixy serves the metadata it harvests from its sources on a single endpoint,
and adds sets to these records. These "virtual" sets are created by extractors using the
metadata itself.

Proaixy is written as a Django website, using Celery as task manager.


Harvesting method
-----------------

Proaixy was designed to harvest from unstable sources i.e. that do not 
exactly comply with the OAI-PMH standard, or return a dirty XML
output, or return various kinds of errors.

The goal is to minimize the amount of records we have to download again
after these failures. Hence proaixy harvests records by batches of records
contained in a small timeframe (one week by default), starting with the
earliest datestamp declared by the interface.

Installation
------------

I recommend installing the following dependencies in a virtualenv:
* http://github.com/wetneb/pyoai
* django
* celery
* django-celery
* psycopg2

 1. Create a postgresql database and put the access details in `proaixy/settings.py`
 2. Run `python manage.py syncdb`. You will be prompted to create an admin account on the interface.
 3. Run `celery --app=proaixy.celery:app worker -B -l INFO`
 4. In parallel, run `python manage.py runserver`

You can access the interface at http://localhost:8000/
The OAI endpoint can be found at http://localhost:8000/oai

Configuration
-------------

Log in to http://localhost:8000/. You will find a form to add a new OAI-PMH source.
Two fields are required:
* The URL of the endpoint
* A short identifier for the source, preferably without spaces and special characters (something
  you can write in an OAI set)
Proaixy will query the endpoint to get more details about it, using the `Identify` verb.

Once it is added, you can harvest it by clicking the appropriate link.





