"""MySQL access layer for metadata discovery and capped read-only queries."""

from typing import Any, Dict, List, Optional, Sequence

from .config import MySQLConfig
from .sql_guard import normalize_max_rows


SYSTEM_SCHEMAS = {"information_schema", "mysql", "performance_schema", "sys"}


class MySQLDatabase:
    def __init__(self, config: MySQLConfig):
        self.config = config

    def connect(self):
        try:
            import mysql.connector  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "mysql-connector-python is required. Install with: python -m pip install mysql-connector-python"
            ) from exc

        kwargs = {
            "host": self.config.host,
            "port": self.config.port,
            "user": self.config.user,
            "password": self.config.password,
            "connection_timeout": self.config.connect_timeout,
        }
        if self.config.database:
            kwargs["database"] = self.config.database
        return mysql.connector.connect(**kwargs)

    def ping(self) -> Dict[str, Any]:
        rows = self._query("SELECT 1 AS ok")
        return {"ok": bool(rows and rows[0].get("ok") == 1)}

    def list_schemas(self, include_system: bool = False) -> List[Dict[str, Any]]:
        rows = self._query(
            """
            SELECT schema_name
            FROM information_schema.schemata
            ORDER BY schema_name
            """
        )
        if include_system:
            return rows
        return [row for row in rows if row.get("schema_name") not in SYSTEM_SCHEMAS]

    def list_tables(self, schema: str) -> List[Dict[str, Any]]:
        return self._query(
            """
            SELECT table_name, table_type, table_rows, table_comment
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (schema,),
        )

    def describe_table(
        self,
        schema: str,
        table: str,
        columns: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT
              table_name,
              ordinal_position,
              column_name,
              column_type,
              is_nullable,
              column_default,
              column_key,
              extra,
              column_comment
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            """
        params: List[Any] = [schema, table]
        if columns is not None:
            column_names = [column for column in columns if column]
            if not column_names:
                return []
            placeholders = ", ".join(["%s"] * len(column_names))
            sql += f"  AND column_name IN ({placeholders})\n"
            params.extend(column_names)
        sql += "            ORDER BY ordinal_position\n"
        return self._query(sql, tuple(params))

    def show_create_table(self, schema: str, table: str) -> Dict[str, Any]:
        sql = "SHOW CREATE TABLE {}.{}".format(quote_identifier(schema), quote_identifier(table))
        rows = self._query(sql)
        if not rows:
            return {"schema": schema, "table": table, "create_table": None}
        row = rows[0]
        return {
            "schema": schema,
            "table": table,
            "create_table": row.get("Create Table") or row.get("Create View"),
        }

    def list_relationships(self, schema: str) -> Dict[str, Any]:
        constraints = self._query(
            """
            SELECT table_name, constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema = %s
            ORDER BY table_name, constraint_type, constraint_name
            """,
            (schema,),
        )
        foreign_keys = self._query(
            """
            SELECT
              table_name,
              column_name,
              referenced_table_name,
              referenced_column_name,
              constraint_name
            FROM information_schema.key_column_usage
            WHERE table_schema = %s
              AND referenced_table_name IS NOT NULL
            ORDER BY table_name, column_name
            """,
            (schema,),
        )
        indexes = self._query(
            """
            SELECT
              table_name,
              index_name,
              non_unique,
              seq_in_index,
              column_name,
              index_type
            FROM information_schema.statistics
            WHERE table_schema = %s
            ORDER BY table_name, index_name, seq_in_index
            """,
            (schema,),
        )
        return {
            "primary_keys": [row for row in constraints if row.get("constraint_type") == "PRIMARY KEY"],
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "candidate_relationships": infer_candidate_relationships(indexes),
        }

    def execute_select(self, sql: str, max_rows: int) -> Dict[str, Any]:
        row_limit = normalize_max_rows(max_rows, self.config.max_rows)
        rows = self._query(sql, limit=row_limit + 1)
        truncated = len(rows) > row_limit
        rows = rows[:row_limit]
        columns = list(rows[0].keys()) if rows else []
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "max_rows": row_limit,
        }

    def _query(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        connection = self.connect()
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(sql, params or ())
                if limit is None:
                    return list(cursor.fetchall())
                return list(cursor.fetchmany(limit))
            finally:
                cursor.close()
        finally:
            connection.close()


def quote_identifier(identifier: str) -> str:
    if not identifier or "\x00" in identifier:
        raise ValueError("Identifier must not be empty or contain NUL")
    return "`{}`".format(identifier.replace("`", "``"))


def infer_candidate_relationships(indexes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    suffixes = ("_id", "_no", "_code", "_uuid")
    for row in indexes:
        column = str(row.get("column_name") or "")
        if column.lower().endswith(suffixes):
            candidates.append(
                {
                    "table_name": row.get("table_name"),
                    "column_name": column,
                    "index_name": row.get("index_name"),
                    "evidence": "indexed foreign-key-like column name",
                    "confidence": "inferred",
                }
            )
    return candidates
