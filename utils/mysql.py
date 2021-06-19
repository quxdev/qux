from django.db import connection
from django.core.management.color import no_style


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
                table = appmodel._meta.db_table
                sqlstr = "ALTER TABLE {:s} AUTO_INCREMENT = 1;".format(table)
                cursor.execute(sqlstr)
