DBcut
=====

.. image:: https://img.shields.io/pypi/v/dbcut.svg
    :target: https://pypi.python.org/pypi/dbcut

.. image:: https://travis-ci.org/itsolutionsfactory/dbcut.svg?branch=master
    :target: https://travis-ci.org/itsolutionsfactory/dbcut
    :alt: CI Status


.. image:: docs/db-cute-small.png
   :alt: DBcut logo
   :align: center


DBcut aims to allow the extraction of lightweight subset of relational production database for development and testing
purpose.


Table of Contents
-----------------

-  `Overview <#overview>`__

   -  `Usage <#usage>`__

-  `Getting started <#getting-started>`__
-  `Under The Hood <#under-the-hood>`__

   -  `Database Reflection and Loading
      Stategy <#database-reflection-and-loading-stategy>`__
   -  `SQL from YAML <#sql-from-yaml>`__
   -  `Extraction Graph <#extraction-graph>`__

Overview
--------

Its main features are:

-  Extract data from large databases.
-  Reinject data into another base.
-  Target and source databases could be based on different DBMS (i.e., MySQL -> PostgreSQL/SQLite).
-  Extraction queries simplified in YAML.
-  Support nested associations.
-  Json and plain SQL export.
-  Reasonable performance.
-  Caching of extractions to accelerate future extractions.

Usage
~~~~~

.. code:: shell

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
     flush       Remove ALL TABLES from the target database and recreate them
     inspect     Check databases content.
     dumpsql     Dump all SQL insert queries.
     dumpjson    Export data to json.
     clear       Remove all data (only) from the target database
     purgecache  Remove all cached queries.

Getting started
---------------

Let's take the following database example:

.. image:: docs/example-simple-db.png
   :alt: Simple Database

We want to extract some users with all related data to our development database.

First, we have to edit the extraction file ``dbcut.yaml`` as follows:

.. code:: yaml

   # dbcut.yml
   databases:
     source_uri: mysql://foo:bar@db-host/prod
     destination_uri: sqlite:///small-dev-database.db

   queries:
     - from: user
       limit: 2

Then, we set the limit to two users, the default limit being 10.

After that, we launch the extraction command with the ``load`` command:

.. code:: shell

   $ dbcut load
    ---> Reflecting database schema from mysql://foo:***@db-host/prod
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

.. code:: shell

   $ ls
   dbcut.yml  small-dev-database.db
   $ sqlite3 small-dev-database.db

.. code:: sql

   sqlite> SELECT id, login FROM user;
   3|jerome
   4|julien

.. code:: sql

   sqlite> SELECT * from comment;
   8|comment jerome 1|3
   9|comment jerome 2|3
   10|comment jerome 3|3

In the following example, we are going to retrieve roles with related groups and permissions. In order to obtain the
best extraction graph, we are going to use the keyword ``include``, which indicated to dbcut that we want to minimize
the number of associated tables (Nested associations).

.. code:: yaml

   queries:
     - from: user
       limit: 2

     - from: role
       include:
         - group
         - permission

It is possible to empty the content of the local database before beginning the extraction with the ``clear`` command.

.. code:: shell

   $ dbcut -y clear load
    ---> Removing all data from sqlite:///small-dev-database.db database
    ---> Reflecting database schema from mysql://foo:***@db-host/prod?charset=utf8
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

.. code:: sql

   sqlite> SELECT * from role;
   1|admin
   2|moderator
   3|user

If we had not used the ``include`` keyword, all tables would have been extracted:

::

           ┌─ⁿ─role_permission┐
           │                  └─¹─permission
       role┤
           └─ⁿ─group┐
                    └─ⁿ─user_group┐
                                  │       ┌─ⁿ─comment
                                  └─¹─user┤
                                          └─ⁿ─vote

To narrow more precisely our extraction, we are now going to limit to roles that can delete a user.

.. code:: yaml

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

.. code:: shell

   $ dbcut -y clear load --last-only
   ...
    ---> Cache key : ffb664a2e69c88fa48db2680daf71d30408bd207
    ---> Executing query
    ---> Fetching objects
    ---> Inserting 14 rows

This time, only the 'admin' role is retrieved:

.. code:: sql

   sqlite> SELECT * from role;
   1|admin

Please note that the filter only applies here to role table (``from``) and not to the permission.

.. code:: sql

   sqlite> SELECT * FROM permission";
   1|delete_comment
   2|delete_vote
   3|delete_user
   4|create_comment
   5|create_vote
   6|create_user

Indeed, we filter the roles based on a value from the permission table, but we do retrieved all permissions associated
to this role.

In the above example, it makes sense that the admin role has all permissions.

Last but not least, we can also retrieve data in json or raw sql format !

.. code:: shell

   $ dbcut dumpjson|dumpsql

.. code:: json

   [
     {
       "password": "julien",
       "vote_collection": [
         {
           "user_id": 4,
           "comment_id": 1,
           "id": 3,
           "rating": 4
         },
         {
           "user_id": 4,
           "comment_id": 3,
           "id": 6,
           "rating": 10
         },
         {
           "user_id": 4,
           "comment_id": 6,
           "id": 13,
           "rating": 10
         }
       ],
       "comment_collection": [],
       "id": 4,
       "login": "julien",
       "user_group_collection": [
         {
           "user_id": 4,
           "group": {
             "name": "Utilisateur",
             "role": {
               "id": 3,
               "role_permission_collection": [
                 {
                   "permission": {
                     "id": 4,
                     "codename": "create_comment",
                     "role_permission_collection": []
                   },

.. code:: sql

   PRAGMA foreign_keys = OFF;

   BEGIN;
   INSERT OR IGNORE INTO permission (id, codename) VALUES (4, 'create_comment');
   INSERT OR IGNORE INTO permission (id, codename) VALUES (5, 'create_vote');
   INSERT OR IGNORE INTO permission (id, codename) VALUES (1, 'delete_comment');
   INSERT OR IGNORE INTO permission (id, codename) VALUES (2, 'delete_vote');
   INSERT OR IGNORE INTO role (id, name) VALUES (3, 'user');
   INSERT OR IGNORE INTO role (id, name) VALUES (2, 'moderator');
   INSERT OR IGNORE INTO user (id, login, password) VALUES (4, 'julien', 'julien');
   INSERT OR IGNORE INTO user (id, login, password) VALUES (3, 'jerome', 'jerome');
   INSERT OR IGNORE INTO "group" (id, name, role_id) VALUES (3, 'Utilisateur', 3);
   INSERT OR IGNORE INTO "group" (id, name, role_id) VALUES (2, 'Moderateur', 2);
   INSERT OR IGNORE INTO comment (id, content, user_id) VALUES (8, 'comment jerome 1', 3);
   INSERT OR IGNORE INTO comment (id, content, user_id) VALUES (9, 'comment jerome 2', 3);
   INSERT OR IGNORE INTO comment (id, content, user_id) VALUES (10, 'comment jerome 3', 3);
   INSERT OR IGNORE INTO role_permission (id, role_id, permission_id) VALUES (12, 3, 4);
   INSERT OR IGNORE INTO role_permission (id, role_id, permission_id) VALUES (13, 3, 5);
   INSERT OR IGNORE INTO role_permission (id, role_id, permission_id) VALUES (7, 2, 4);
   INSERT OR IGNORE INTO role_permission (id, role_id, permission_id) VALUES (8, 2, 5);
   INSERT OR IGNORE INTO role_permission (id, role_id, permission_id) VALUES (10, 2, 1);
   INSERT OR IGNORE INTO role_permission (id, role_id, permission_id) VALUES (11, 2, 2);
   INSERT OR IGNORE INTO user_group (id, user_id, group_id) VALUES (4, 4, 3);
   INSERT OR IGNORE INTO user_group (id, user_id, group_id) VALUES (3, 3, 2);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (3, 4, 4, 1);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (6, 10, 4, 3);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (13, 10, 4, 6);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (2, 5, 3, 1);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (5, 1, 3, 2);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (7, 10, 3, 3);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (10, 6, 3, 1);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (11, 5, 3, 5);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (12, 6, 3, 6);
   INSERT OR IGNORE INTO vote (id, rating, user_id, comment_id) VALUES (19, 10, 3, 10);
   COMMIT;

Under The Hood
--------------

Database Reflection and Loading Stategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DBcut heavily uses SQLAlchemy, the SQL toolkit and Object Relational Mapper for Python. The ORM makes it possible to
free ourselves from the SQL direct manipulation, but that is not all. SQLAlchemy offers a range of toolkits that enable
us to programmatically build all SQL queries useful to DBcut. This include both the schema creation and all of its
properties, the select, join and insert queries… no matter which DBMS is used (PostgreSQL, MySQL, SQLite, oracle etc.).

One of the most important features of DBcut is that the user does not need to know or provide the source database
schema to use it. First of all, DBcut will inspect the source database and retrieve all metadata. This action is what we
call: *Database Reflection*.

.. image:: docs/database_reflection.png
   :alt: Database Reflection


The MetaData object store all the collection of metadata entities. DBcut will alter this MetaData object to make it
compatible with most DBMS. For example, the names of indexes or foreign keys can be too long for SQLite but not for
MYSQL. Sometimes, it also changes the types of the column to make it match what is expected in the target database.
(``mysql.TINYINT`` became ``SMALLINT`` in SQLite and PostgreSQL)

Once the MetaData object is complete, we can create the new database which is almost identical to the source database
(except some compatibility adjustments)

DBcut will generate and launch extraction request on the source database. The data thus obtained will be detached from
the first SQLAlchemy session to be attached to the new session in the target database. This is where the SQLAlchemy
magic happens: the same request will be used to extract data from the source database and to load them into the target
database. Indeed, in the first case (query/fetch), it will be translated into SQL ``SELECT`` queries and in the second
case, into SQL ``INSERT`` statements (load).

SQL from YAML
~~~~~~~~~~~~~

One of the goals of DBcut is to allow quick writing of extraction requests. Most of the time, to write an extraction
request, not much information is needed: only the main table name, hoping to retrieve the maximum number of related
data as possible.

The idea was to find a sufficiently concise syntax that allows us to build the most complete extraction requests with
the minimum effort.

The YAML came to us naturally as it is pleasant to read, easy to understand and to edit for humans.

The ``dbcut.yml`` file is both used to configure DBcut and to write
extraction requests.

.. code:: yaml

   databases:
     source_uri: mysql://chinook:chinook@192.168.66.66/chinook
     destination_uri: sqlite:///chinook.db

   queries:
     - from: customer_customer

To write an extraction request, only the keyword ``from`` is mandatory. However, other keywords can be added to reduce
the size of data to retreive.

.. code:: yaml

     - from: contracts_customer
       where:
         brand: 2
       limit: 100
       backref_limit: 500
       backref_depth: 2
       join_depth: 5
       exclude:
       - django_admin_log
       - django_session
       include: []

Unlike the SQL queries, an extraction request using DBcut automatically and recursively loads all associated relations
(See `Extraction Graph <#extraction-graph>`__). All these options are filtering and reducing options that prevents from
slowing down the extraction process.

Finally, with the scope of making the extraction requests as compact as possible, we can add default values to most of
these options:

.. code:: yaml

   default_limit: 100
   default_backref_limit: 500

   default_backref_depth: 2
   default_join_depth: 5

   global_exclude:
     - django_admin_log
     - django_session

Extraction Graph
~~~~~~~~~~~~~~~~

To build an extraction request, we first build its extraction graph.

An extraction graph is a subset of the complete graph of database relations. Every node represents a table, and each
link represents a relation between two tables. The link direction is defined by the foreign key.

To build this graph, we use the ``MetaData`` object (See `Database Reflection and Loading Stategy
<#database-reflection-and-loading-stategy>`__).

Let's use the following database schema:


.. image:: docs/chinook_schema.png
   :alt: Database chinook schema


The retrieved metadata during the database reflection are used to build
the following complete graph of relations:


.. image:: docs/chinook_uml_graph.png
   :alt: Complete graph of relations


To build the extraction graph, we browse the complete graph starting
from the table used in the ``from`` instruction. The browsing only stops
if :

-  the link has already been browsed
-  the table is explicitly excluded
-  the maximum depth is reached

For the following request:

.. code:: yaml

   queries:
     - from: customer_customer

The generated extraction graph is:


.. image:: docs/dbcut-load-chinook.png
   :alt: Generated extraction graph


Please note that we handle the two types of relations : one-to-many relations (noted ``1`` in the extraction graph) and
many-to-many relations (noted ``n``).
