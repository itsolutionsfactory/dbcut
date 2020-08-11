CHANGELOG
=========

Version 0.1.5
-------------

Released on August 11th 2020

Bug fixed:

- Fixed dumpjson regression
- `dumpsql` prints only create and insert sql statements
- Fixed query caching mechanism
- Prepared all mapper objects correctly when metadata is cached
- Various minor bug fixes

Version 0.1.4
-------------

Bug fixed:

- Fixed TypeError exception
- Defined a max length for indexes on TEXT column on mysql databases

Released on May 07th 2020

Version 0.1.3
-------------

Released on November 27th 2019

Bug fixes:

- Determistic cache key generation.
- `clear` cmd delete only existing table.  

First release on PyPI.


Version 0.1.2
-------------

Released on November 15th 2019


* Removed SAWarning about loading declaratives classes twice
* Fixed syntax error on sql truncate queries
* Fixed query parsing when mixing attributes in the same query

Version 0.1.1
-------------

Released on November 14th 2019


* Removed universal wheel package, only python3 is supported

Version 0.1.0
-------------

Released on November 14th 2019
