from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mysql_readonly_mcp.sql_guard import SqlSafetyError  # noqa: E402
from mysql_readonly_mcp.tools import MySQLTools  # noqa: E402


class FakeDB:
    def __init__(self):
        self.executed = []

    def ping(self):
        return {"ok": True}

    def list_schemas(self, include_system=False):
        return [{"schema_name": "app"}]

    def list_tables(self, schema):
        return [{"table_name": "users", "table_type": "BASE TABLE"}]

    def describe_table(self, schema, table):
        return [{"column_name": "id", "column_type": "bigint"}]

    def show_create_table(self, schema, table):
        return {"table": table, "create_table": "CREATE TABLE `users` (`id` bigint)"}

    def list_relationships(self, schema):
        return {"primary_keys": [], "foreign_keys": [], "indexes": [], "candidate_relationships": []}

    def execute_select(self, sql, max_rows):
        self.executed.append((sql, max_rows))
        return {"columns": ["id"], "rows": [{"id": 1}], "row_count": 1, "truncated": False}


def test_execute_select_rejects_unsafe_sql_before_db_call():
    db = FakeDB()
    tools = MySQLTools(db, configured_max_rows=100)

    with pytest.raises(SqlSafetyError):
        tools.mysql_execute_select("DROP TABLE users", max_rows=10)

    assert db.executed == []


def test_execute_select_normalizes_sql_and_caps_rows():
    db = FakeDB()
    tools = MySQLTools(db, configured_max_rows=50)

    result = tools.mysql_execute_select(" SELECT * FROM users; ", max_rows=500)

    assert result["row_count"] == 1
    assert db.executed == [("SELECT * FROM users", 50)]


def test_execute_select_allows_cte():
    db = FakeDB()
    tools = MySQLTools(db, configured_max_rows=100)

    tools.mysql_execute_select("WITH u AS (SELECT * FROM users) SELECT * FROM u", max_rows=5)

    assert db.executed == [("WITH u AS (SELECT * FROM users) SELECT * FROM u", 5)]


def test_metadata_tools_delegate_to_db():
    db = FakeDB()
    tools = MySQLTools(db)

    assert tools.mysql_ping() == {"ok": True}
    assert tools.mysql_list_schemas() == [{"schema_name": "app"}]
    assert tools.mysql_list_tables("app")[0]["table_name"] == "users"
    assert tools.mysql_describe_table("app", "users")[0]["column_name"] == "id"
    assert "CREATE TABLE" in tools.mysql_show_create_table("app", "users")["create_table"]
    assert tools.mysql_list_relationships("app")["indexes"] == []
