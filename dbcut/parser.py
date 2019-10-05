# -*- coding: utf-8 -*-
import mlalchemy.structures
from mlalchemy.constants import OP_NOT, OP_OR, ORDER_ASC, ORDER_DESC
from mlalchemy.errors import (InvalidComparatorError, InvalidFieldError,
                              InvalidTableError)
from mlalchemy.structures import MLQuery as BaseMLQuery
from mlalchemy.structures import MLQueryFragment as BaseMLQueryFragment
from mlalchemy.structures import logger
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.sql.expression import and_, not_, or_

from .utils import uncache_module


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
    def to_sqlalchemy(self, query):
        tables = query.session.bind._db.models
        table = query.model_class
        filter_criteria = []
        for clause in self.clauses:
            field_parts = clause.field.split(".")
            if not field_parts[0] == clause.field:
                table_name = field_parts[0]
                field = field_parts[1]
                if table_name not in tables:
                    raise InvalidTableError(
                        "Table does not exist in tables dictionary: %s" % table_name
                    )
                if table_name not in query.relation_tree.flatten:
                    raise InvalidTableError(
                        "Table '%s' is missing from the current relation tree"
                        % table_name
                    )
                table = tables[table_name]
                clause.field = field
            filter_criteria.append(clause.to_sqlalchemy(table))
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


def parse_query(qd):
    from mlalchemy.parser import parse_query as mlalchemy_parse_query

    return mlalchemy_parse_query(qd)
