"""MySQL-specific helpers.

``resetsequence(appmodels)`` — reset auto-increment sequences for the given
model classes back to 1. Uses Django's `sequence_reset_sql` when the backend
supports it; for MySQL (which doesn't), falls back to issuing
``ALTER TABLE <table> AUTO_INCREMENT = 1`` per model. Used by
``manage.py resetapp --wipe`` to leave the schema in a "fresh-install" state
after deleting all rows.

Table names are quoted via ``connection.ops.quote_name`` to avoid SQL
injection from app-config-derived table names.
"""

from django.core.management.color import no_style
from django.db import connection


def resetsequence(appmodels):
    if appmodels is None:
        return

    with connection.cursor() as cursor:
        sequence_sql = connection.ops.sequence_reset_sql(no_style(), appmodels)
        if sequence_sql:
            for sqlstr in sequence_sql:
                cursor.execute(sqlstr)
        else:
            # django doesn't return anything with sequence_sql
            for appmodel in appmodels:
                # noinspection PyProtectedMember
                table = connection.ops.quote_name(appmodel._meta.db_table)
                sqlstr = f"ALTER TABLE {table} AUTO_INCREMENT = 1;"
                cursor.execute(sqlstr)
