"""Tool behavior for the MySQL read-only MCP server."""

from typing import Optional, Sequence

from .sql_guard import assert_readonly_select, normalize_max_rows


class MySQLTools:
    def __init__(self, db, configured_max_rows: int = 100):
        self.db = db
        self.configured_max_rows = configured_max_rows

    def mysql_ping(self):
        return self.db.ping()

    def mysql_list_schemas(self, include_system: bool = False):
        return self.db.list_schemas(include_system=include_system)

    def mysql_list_tables(self, schema: str):
        return self.db.list_tables(schema)

    def mysql_describe_table(
        self,
        schema: str,
        table: str,
        columns: Optional[Sequence[str]] = None,
    ):
        return self.db.describe_table(schema, table, columns=columns)

    def mysql_show_create_table(self, schema: str, table: str):
        return self.db.show_create_table(schema, table)

    def mysql_list_relationships(self, schema: str):
        return self.db.list_relationships(schema)

    def mysql_execute_select(self, sql: str, max_rows: Optional[int] = None):
        safe_sql = assert_readonly_select(sql)
        safe_max_rows = normalize_max_rows(max_rows, self.configured_max_rows)
        return self.db.execute_select(safe_sql, safe_max_rows)
