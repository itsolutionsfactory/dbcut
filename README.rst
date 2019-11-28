
DBcut
=====

.. image:: https://img.shields.io/pypi/v/dbcut.svg
    :target: https://pypi.python.org/pypi/dbcut

.. image:: https://travis-ci.org/itsolutionsfactory/dbcut.svg?branch=master
    :target: https://travis-ci.org/itsolutionsfactory/dbcut
    :alt: CI Status


Extract a lightweight subset of your relational production database for development and testing purpose.

Features
--------


* Extract data from large databases.
* Reinject data into another base.
* Target and source databases could be based on different SGBD (i.e., MySQL -> PostgreSQL/SQLite).
* Extraction queries simplified in YAML.
* Support nested associations.
* Json and plain SQL export.
* Caching of extractions to accelerate future extractions.

Usage
-----

.. code-block::

   Usage: dbcut [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

     Extract a lightweight subset of your production DB for development and
     testing purpose.

   Options:
     -c, --config PATH    Configuration file
     --version            Show the version and exit.
     -y, --force-yes      Never prompts for user intervention
     -i, --interactive    Prompts for user intervention.
     --quiet, --no-quiet  Suppresses most warning and diagnostic messages.
     --debug              Enables debug mode.
     --verbose            Enables verbose output.
     -h, --help           Show this message and exit.

   Commands:
     load        Extract and load data to the target database.
     flush       Purge cache, remove ALL TABLES from the target database and...
     inspect     Check databases content.
     dumpsql     Dump all SQL insert queries.
     dumpjson    Export data to json.
     purgecache  Remove all cached queries.
     clear       Remove all data (only) from the target database

Getting started
---------------

Let's take the following database example:


.. image:: https://raw.githubusercontent.com/itsolutionsfactory/dbcut/master/demo/example-simple-db.png?raw=true
   :target: https://raw.githubusercontent.com/itsolutionsfactory/dbcut/master/demo/example-simple-db.png?raw=true
   :alt: Simple Database


We want to extract some users with all related data to our development database.

Let's first edit the extraction file ``dbcut.yaml`` as follows:

.. code-block:: shell

   $ cd myprojet
   $ vim dbcut.yml

.. code-block:: yaml

   databases:
     source_uri: mysql://prod:prod@cluster-prod01.mycompagny.com/prod
     destination_uri: sqlite:///small-dev-database.db

   queries:
     - from: user
       limit: 2
   `

Then, let's set the limit to two users, the default limit being 10.

After that, let's launch the extraction command with the ``load`` command:

.. code-block:: shell

   $ dbcut load
    ---> Reflecting database schema from mysql://prod:***@cluster-prod01.mycompagny.com/prod
    ---> Creating new sqlite:///small-dev-database.db database
    ---> Creating all tables and relations on sqlite:///small-dev-database.db

   Query 1/1 :

       from: user
       limit: 2
       backref_limit: 10
       backref_depth: 5
       join_depth: 5
       exclude: []
       include: []


        ┌─ⁿ─comment
        ├─ⁿ─vote
    user┤
        └─ⁿ─user_group┐
                      └─¹─group┐
                               └─¹─role┐
                                       └─ⁿ─role_permission┐
                                                          └─¹─permission


   8 tables loaded

    ---> Cache key : 4a468c3555074890b7c342c0a575f29d47145821
    ---> Executing query
    ---> Fetching objects
    ---> Inserting 31 rows

We can check the data on our new database :

.. code-block:: shell

   $ ls
   dbcut.yml  small-dev-database.db

   $ sqlite3 small-dev-database.db <<<"SELECT id, login FROM user"
   3|jerome
   4|julien

In the following example, we are going to retrieve roles with related groups and permissions.
In order to obtain the best extraction graph possible, we are going to use the keyword ``include``\ , which indicated to dbcut that
we want to minimize the number of associated tables (Nested associations).

.. code-block:: yaml

   queries:
     - from: user
       limit: 2

     - from: role
       include:
         - group
         - permission

It is possible to empty the content of the local database before beginning the extraction with the ``clear`` command.

.. code-block:: shell

   $ dbcut -y clear load
    ---> Removing all data from sqlite:///small-dev-database.db database
    ---> Reflecting database schema from mysql://prod:***@cluster-prod01.mycompagny.com/prod?charset=utf8
    ---> Creating all tables and relations on sqlite:///small-dev-database.db

   Query 1/2 :

       from: user
       limit: 2
       backref_limit: 10
       backref_depth: 5
       join_depth: 5
       exclude: []
       include: []


        ┌─ⁿ─comment
        ├─ⁿ─vote
    user┤
        └─ⁿ─user_group┐
                      └─¹─group┐
                               └─¹─role┐
                                       └─ⁿ─role_permission┐
                                                          └─¹─permission


   8 tables loaded

    ---> Cache key : 4a468c3555074890b7c342c0a575f29d47145821
    ---> Using cache (2 elements)
    ---> Fetching objects
    ---> Inserting 31 rows

   Query 2/2 :

       from: role
       limit: 10
       backref_limit: 10
       backref_depth: null
       join_depth: null
       exclude: []
       include:
       - group
       - permission


        ┌─ⁿ─group
    role┤
        └─ⁿ─role_permission┐
                           └─¹─permission


   4 tables loaded

    ---> Cache key : 5029d84dbb2bc75a7df898dd94df93b395e91e44
    ---> Executing query
    ---> Fetching objects
    ---> Inserting 22 rows

As you can see in the first query, the cache was used and there was thus no interaction with the source database.

This query allowed the extraction of all roles:

.. code-block::

   $ sqlite3 small-dev-database.db  <<<"SELECT * from role"
   1|admin
   2|moderator
   3|user

If we had not used the ``include`` keyword, all tables would have been extracted:

.. code-block::

        ┌─ⁿ─role_permission┐
        │                  └─¹─permission
    role┤
        └─ⁿ─group┐
                 └─ⁿ─user_group┐
                               │       ┌─ⁿ─comment
                               └─¹─user┤
                                       └─ⁿ─vote

To narrow more precisely our extraction, we are now going to limit to roles that can delete a user.

.. code-block:: yaml

   queries:
     - from: user
       limit: 2

     - from: role
       include:
         - group
         - permission
       where:
         permission.codename: 'delete_user'

Only the last extraction rule is relaunched with the ``--last-only`` option.

.. code-block:: yaml

   $ dbcut -y clear load --last-only
   ...
    ---> Cache key : ffb664a2e69c88fa48db2680daf71d30408bd207
    ---> Executing query
    ---> Fetching objects
    ---> Inserting 14 rows

This time, only the 'admin' role is retrieved:

.. code-block:: shell

   $ sqlite3 small-dev-database.db  <<<"SELECT * FROM role"
   1|admin

Please note that the filter only applies here to the role table (\ ``from``\ ) and not to the permission table.

.. code-block:: shell

   $ sqlite3 small-dev-database.db  <<<"SELECT * FROM permission"
   1|delete_comment
   2|delete_vote
   3|delete_user
   4|create_comment
   5|create_vote
   6|create_user

Indeed, we filter the roles based on a value from the permission table, but we do retrieved all permissions associated to this role.

In the above example, it makes sense that the admin role has all permissions.
