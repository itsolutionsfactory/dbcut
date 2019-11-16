# -*- coding: utf-8 -*-
from collections import OrderedDict

import mlalchemy.structures
from mlalchemy.constants import OP_NOT, OP_OR, ORDER_ASC, ORDER_DESC
from mlalchemy.errors import InvalidFieldError, InvalidTableError
from mlalchemy.structures import MLQuery as BaseMLQuery
from mlalchemy.structures import MLQueryFragment as BaseMLQueryFragment
from mlalchemy.structures import logger
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.sql.expression import and_, not_, or_

# from .models import BaseModel
from .utils import merge_dicts, uncache_module


class MLQuery(BaseMLQuery):
    def to_query(self, session, tables):
        if not isinstance(tables, dict):
            raise TypeError(
                "Supplied tables structure for MLQuery-to-SQLAlchemy query conversion must be a dictionary"
            )
        if self.table not in tables:
            raise InvalidTableError(
                "Table does not exist in tables dictionary: %s" % self.table
            )
        logger.debug(
            'Attempting to build SQLAlchemy query for table "%s":\n%s'
            % (self.table, self)
        )
        table = tables[self.table]
        return session.query(table)

    def apply_filters(self, query):
        table = query.model_class

        if self.query_fragment is not None:
            query = query.filter(self.query_fragment.to_sqlalchemy(query))

        if self.order_by:
            criteria = []
            for order_by in self.order_by:
                field, direction = [i for i in order_by.items()][0]
                criterion = getattr(table, field)
                if not isinstance(criterion, QueryableAttribute):
                    raise InvalidFieldError(
                        "Invalid field for specified table: %s" % field
                    )

                if direction == ORDER_ASC:
                    criterion = criterion.asc()
                elif direction == ORDER_DESC:
                    criterion = criterion.desc()
                criteria.append(criterion)
            query = query.order_by(*criteria)
        else:
            ordering_keys = query.model_class._default_ordering
            if ordering_keys:
                query = query.order_by(*ordering_keys)

        if self.offset is not None:
            query = query.offset(self.offset)

        if self.limit is not None:
            query = query.limit(self.limit)

        return query


class MLQueryFragment(BaseMLQueryFragment):
    def to_sqlalchemy(self, query_or_table):
        from .query import BaseQuery

        tables = []
        table = query_or_table
        if isinstance(query_or_table, BaseQuery):
            table = query_or_table.model_class
            tables = query_or_table.session.bind._db.models
        else:
            table = query_or_table
            tables = query_or_table._db.models

        filter_criteria = []
        for clause in self.clauses:
            field_parts = clause.field.split(".")
            _table = table
            if not field_parts[0] == clause.field:
                table_name = field_parts[0]
                field = field_parts[1]
                if table_name not in tables:
                    raise InvalidTableError(
                        "Table does not exist in tables dictionary: %s" % table_name
                    )
                table = tables[table_name]
                clause.field = field
            filter_criteria.append(clause.to_sqlalchemy(table))
            table = _table
        filter_criteria.extend(
            [sub_frag.to_sqlalchemy(table) for sub_frag in self.sub_fragments]
        )

        if self.op == OP_OR:
            return or_(*filter_criteria)
        elif self.op == OP_NOT:
            return not_(*filter_criteria)

        return and_(*filter_criteria)


mlalchemy.structures.MLQuery = MLQuery
mlalchemy.structures.MLQueryFragment = MLQueryFragment
uncache_module(
    exclude=["mlalchemy.structures", "mlalchemy.constants", "mlalchemy.errors"]
)


def parse_query(qd, session, config):
    """Parses the given query dictionary to produce a BaseQuery object.
    """
    from mlalchemy.parser import parse_query as mlalchemy_parse_query

    defaults = {
        "limit": config["default_limit"],
        "backref_limit": config["default_backref_limit"],
        "backref_depth": config["default_backref_depth"],
        "join_depth": config["default_join_depth"],
        "exclude": [],
        "include": [],
    }
    qd.setdefault("limit", defaults["limit"])

    full_qd = merge_dicts(defaults, qd)

    if qd["limit"] in (None, False):
        qd.pop("limit")

    if isinstance(full_qd["exclude"], str):
        full_qd["exclude"] = [full_qd["exclude"]]

    full_qd["exclude"] = list(set(full_qd["exclude"] + config["global_exclude"]))

    if isinstance(full_qd["include"], str):
        full_qd["include"] = [full_qd["include"]]

    mlquery = mlalchemy_parse_query(qd)

    query = mlquery.to_query(session, session.bind._db.models)

    order_by = full_qd.pop("order-by", None)
    if order_by:
        full_qd["order_by"] = order_by

    qd_key_sort = [
        "from",
        "where",
        "order_by",
        "offset",
        "limit",
        "backref_limit",
        "backref_depth",
        "join_depth",
        "exclude",
        "include",
    ]

    if full_qd["include"]:
        full_qd["join_depth"] = full_qd["backref_depth"] = None
    else:
        full_qd["join_depth"] = full_qd["join_depth"] or 0
        full_qd["backref_depth"] = full_qd["backref_depth"] or 0

    query.query_dict = OrderedDict(
        sorted(full_qd.items(), key=lambda x: qd_key_sort.index(x[0]))
    )

    query = query.with_loaded_relations(
        full_qd["join_depth"],
        full_qd["backref_depth"],
        full_qd["exclude"],
        full_qd["include"],
    )

    query = mlquery.apply_filters(query)

    return query
