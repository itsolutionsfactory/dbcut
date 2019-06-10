# -*- coding: utf-8 -*-
from __future__ import absolute_import

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import sqla_compat
from sqlalchemy import MetaData

from .compat import to_unicode
from .helpers import blue, red, yellow


SUPPORTED_ALEMBIC_OPERATIONS = {
    'remove_column': 'drop column %s from table %s',
    'add_table': 'create table %s',
    'add_column': 'add column %s to table %s',
    'modify_nullable': 'modify column %s.%s by setting nullable property to %s',
    'modify_type': 'modify column %s.%s type to %s',
    'remove_index': 'drop index %s(%s)',
    'add_index': 'create index %s(%s)',
    'add_fk': 'add foreign key constraint %s on table %s (%s) to table %s (%s)',
}


def alembic_generate_diff(from_engine, to_engine):
    opts = {'compare_type': True}
    supported_operations = list(SUPPORTED_ALEMBIC_OPERATIONS.keys())
    mc = MigrationContext.configure(to_engine.connect(), opts=opts)
    from_metadata = MetaData()
    from_metadata.reflect(bind=from_engine)

    def all_diffs():
        for diff in compare_metadata(mc, from_metadata):
            if isinstance(diff[0], tuple):
                op_name = diff[0][0]
            else:
                op_name = diff[0]
            if True:
                yield op_name, diff
    key_sort = lambda x: supported_operations.index(x[0])
    return sorted(all_diffs(), key=key_sort)


def alembic_apply_diff(ctx, op, op_name, diff):
    supported_operations = SUPPORTED_ALEMBIC_OPERATIONS.keys()
    if op_name not in supported_operations:
        raise ValueError("Unsupported '%s' operation" % op_name)

    if op_name == "add_table":
        table_name = diff[1].name
        columns = [c.copy() for c in diff[1].columns]
        msg = SUPPORTED_ALEMBIC_OPERATIONS[op_name] % table_name
        op_callback = lambda: op.create_table(table_name, *columns)
    elif op_name in ('add_column', 'remove_column'):
        column = diff[3].copy()
        table_name = diff[2]
        if 'add' in op_name:
            op_callback = lambda: op.add_column(diff[2], column)
        else:
            op_callback = lambda: op.drop_column(diff[2], column.name)
        msg = SUPPORTED_ALEMBIC_OPERATIONS[op_name] % (column.name, table_name)
    elif op_name in ('remove_index', 'add_index'):
        index = diff[1]
        columns = [i for i in index.columns]
        table_name = index.table.name
        index_colums = ()
        for column in columns:
            index_colums += ("%s.%s" % (column.table.name, column.name),)
        if 'add' in op_name:
            args = (index.name, table_name, [c.name for c in columns],)
            kwargs = {'unique': index.unique}
            op_callback = lambda: op.create_index(*args, **kwargs)
        else:
            op_callback = lambda: op.drop_index(index.name)
        msg = SUPPORTED_ALEMBIC_OPERATIONS[op_name] \
            % (index.name, ",".join(index_colums))
    elif op_name in ('modify_type',):
        table_name = diff[0][2]
        column_name = diff[0][3]
        kwargs = diff[0][4]
        type_ = diff[0][6]

        def op_callback():
            op.alter_column(table_name, column_name, server_default=None)
            op.alter_column(table_name, column_name, type_=type_, **kwargs)

        msg = SUPPORTED_ALEMBIC_OPERATIONS[op_name] \
            % (table_name, column_name, type_)
    elif op_name in ('modify_nullable',):
        table_name = diff[0][2]
        column_name = diff[0][3]
        kwargs = diff[0][4]
        nullable = diff[0][6]
        existing_type = kwargs['existing_type']

        def op_callback():
            op.alter_column(table_name, column_name,
                            nullable=nullable,
                            existing_type=existing_type)
        msg = SUPPORTED_ALEMBIC_OPERATIONS[op_name] \
            % (table_name, column_name, nullable)
    elif op_name == 'add_fk':
        constraint = diff[1]
        (
            source_schema,
            source_table,
            local_cols,
            target_schema,
            referent_table,
            remote_cols,
            onupdate,
            ondelete,
            deferrable,
            initially,
        ) = sqla_compat._fk_spec(constraint)

        msg = SUPPORTED_ALEMBIC_OPERATIONS[op_name] \
            % (constraint.name, source_table, ','.join(local_cols),
               referent_table, ','.join(remote_cols))

        def op_callback():
            op.create_foreign_key(constraint.name,
                                  source_table, referent_table,
                                  local_cols, remote_cols,
                                  onupdate=onupdate,
                                  ondelete=ondelete,
                                  deferrable=deferrable,
                                  initially=initially)

    try:
        if msg is not None:
            ctx.log("%s ~> %s" % (yellow('upgrade'), msg))
        op_callback()
    except Exception as ex:
        ctx.log(*red(to_unicode(ex)).splitlines(), prefix=(' ' * 9))


def alembic_sync_schema(ctx, from_engine, to_engine):
    message = blue('compare') + ' ~> databases schemas'
    ctx.log(message + ' (in progress)')
    diffs = list(alembic_generate_diff(from_engine, to_engine))

    ctx.log("%s (%s)" % (message, blue("%s changes" % len(diffs))))

    mc = MigrationContext.configure(to_engine.connect())
    op = Operations(mc)

    for op_name, diff in diffs:
        alembic_apply_diff(ctx, op, op_name, diff)
