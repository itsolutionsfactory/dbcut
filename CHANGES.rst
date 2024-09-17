CHANGELOG
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <http://keepachangelog.com/en/1.0.0/>`_, and this project adheres to `Semantic Versioning <http://semver.org/spec/v2.0.0.html>`_.

Version 0.6.2
------------------

Released on September 13th 2024

Added
-----
- Geometry field in sqlalchemy

Version 0.6.1.dev0
------------------

**unreleased**

Version 0.6.0
-------------

Released on April 13th 2021

Added
-----
- Better support for tables without primary key
- Load all many-to-many relationships just like one-to-many ones

Version 0.5.0
-------------

Released on April 09th 2021


Added
-----

- Added support of SQLAlchemy 1.4

Version 0.4.1
-------------

Released on April 01st 2021

Changed
-------
- Downgrade sqlalchemy requirement to <=1.4 versions to prevent crashing


Version 0.4.0
-------------

Released on March 12th 2021

Changed
-------
- Ensure that generated names for SQLAlchemy relationships do not conflict with columns names
- Always generate unique indexes on sqlite
- Translate mysql `current_timestamp()` to `CURRENT_TIMESTAMP` on sqlite

Version 0.3.1
-------------

Released on March 05th 2021

Added
~~~~~

- New experimental class Recorder that record all SQL interactions in order to replay them offline (for testing purpose)

Version 0.2.0
-------------

Released on August 21st 2020

Added
~~~~~
- Always enable SQLAlchemy post_update to avoid circular dependecies
- Disable all cache if `cache` config key is set to `no`
- Do not globally exclude already loaded relations from the other extraction graph branches
- Improved cyclical relations loading in the extraction graph

Changed
~~~~~~~
- Store cache by dbcut version

Removed
~~~~~~~
- Removed marshmallow serialization and prefer builtin json


Version 0.1.6
-------------

Released on August 20th 2020

Changed
~~~~~~~
- `flush` purges the cache only when `--with-cache` is passed

Fixed
~~~~~
- Load only transient mapper objects to force sqlalchemy to generate sql insert queries


Version 0.1.5
-------------

Released on August 11th 2020

Changed
~~~~~~~
- `dumpsql` prints only create and insert sql statements

Fixed
~~~~~
- Fixed dumpjson regression
- Fixed query caching mechanism
- Prepared all mapper objects correctly when metadata is cached
- Various minor bug fixes


Version 0.1.4
-------------

Released on May 07th 2020

Fixed
~~~~~
- Fixed TypeError exception
- Defined a max length for indexes on TEXT column on mysql databases


Version 0.1.3
-------------

Released on November 27th 2019

Changed
~~~~~~~
- `clear` cmd delete only existing table.

Fixed
~~~~~
- Determistic cache key generation.

First release on PyPI.
