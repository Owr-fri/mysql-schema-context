from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mysql_readonly_mcp.db import MySQLDatabase  # noqa: E402


def test_describe_table_filters_multiple_columns_with_one_metadata_query(monkeypatch):
    db = MySQLDatabase(config=None)
    calls = []

    def fake_query(sql, params=None, limit=None):
        calls.append((sql, params, limit))
        return []

    monkeypatch.setattr(db, "_query", fake_query)

    db.describe_table("app", "users", columns=["id", "email"])

    assert len(calls) == 1
    sql, params, limit = calls[0]
    assert "column_name IN (%s, %s)" in sql
    assert params == ("app", "users", "id", "email")
    assert limit is None


def test_describe_table_without_column_filter_keeps_table_wide_query(monkeypatch):
    db = MySQLDatabase(config=None)
    calls = []

    def fake_query(sql, params=None, limit=None):
        calls.append((sql, params, limit))
        return []

    monkeypatch.setattr(db, "_query", fake_query)

    db.describe_table("app", "users")

    assert len(calls) == 1
    sql, params, limit = calls[0]
    assert "column_name IN" not in sql
    assert params == ("app", "users")
    assert limit is None
