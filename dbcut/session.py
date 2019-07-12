# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from .utils import merge_dicts


class BaseSession(Session):
    def __init__(self, db, **options):
        self.db = db
        bind = options.pop("bind", None) or db.engine
        query_cls = options.pop("query_cls", None) or db.query_class

        session_options = merge_dicts(
            dict(autocommit=False, autoflush=False), db._session_options
        )

        Session.__init__(self, bind=bind, query_cls=query_cls, **session_options)


class SessionProperty(object):

    _scoped_sessions = {}

    def __init__(self, db=None):
        self.db = db

    def _create_session_sessionmaker(self, db, options):
        return sessionmaker(class_=BaseSession, db=db, **options)

    def _create_scoped_session(self, db):
        options = db._session_options
        session_factory = self._create_session_sessionmaker(db, options)
        return scoped_session(session_factory)

    def __get__(self, obj, type_):
        if self.db is not None:
            obj = self.db
        if obj is not None:

            if obj not in self._scoped_sessions:
                self._scoped_sessions[obj] = self._create_scoped_session(obj)

            scoped_session = self._scoped_sessions[obj]

            return scoped_session
        return self
