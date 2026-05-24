from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mysql_readonly_mcp.sql_guard import (  # noqa: E402
    SqlSafetyError,
    assert_readonly_select,
    normalize_max_rows,
    split_statements,
    strip_sql_comments,
    validate_readonly_select,
)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id, status FROM orders",
        " select 1 ",
        "SELECT 'update is just text' AS note",
        "SELECT id FROM orders WHERE note = 'DROP TABLE is text'",
        "WITH recent_orders AS (SELECT * FROM orders) SELECT * FROM recent_orders",
    ],
)
def test_validate_readonly_select_accepts_safe_selects(sql):
    assert validate_readonly_select(sql) == sql.strip().rstrip(";").strip()


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "   ",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "INSERT INTO users(id) VALUES (1)",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN note TEXT",
        "CREATE TABLE x(id INT)",
        "TRUNCATE TABLE users",
        "SET sql_safe_updates = 0",
        "USE prod",
        "CALL dangerous_proc()",
        "SELECT * FROM users INTO OUTFILE '/tmp/users.csv'",
        "SELECT id INTO @user_id FROM users LIMIT 1",
        "SELECT LOAD_FILE('/etc/passwd')",
        "SELECT SLEEP(10)",
        "LOAD DATA LOCAL INFILE '/tmp/users.csv' INTO TABLE users",
    ],
)
def test_validate_readonly_select_rejects_unsafe_sql(sql):
    with pytest.raises(SqlSafetyError):
        validate_readonly_select(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; SELECT 2",
        "SELECT 1; DROP TABLE users",
        "SELECT 1 /* comment */; SELECT 2",
        "SELECT 1; -- hidden second statement\nSELECT 2",
    ],
)
def test_validate_readonly_select_rejects_multiple_statements(sql):
    with pytest.raises(SqlSafetyError):
        validate_readonly_select(sql)


def test_trailing_semicolon_is_allowed():
    assert validate_readonly_select("SELECT 1;") == "SELECT 1"


def test_strip_sql_comments_preserves_string_literals():
    sql = "SELECT '-- not comment' AS a, '/* not comment */' AS b -- real comment"
    stripped = strip_sql_comments(sql)
    assert "'-- not comment'" in stripped
    assert "'/* not comment */'" in stripped
    assert "real comment" not in stripped


def test_split_statements_ignores_semicolon_inside_string():
    assert split_statements("SELECT ';' AS semi;") == ["SELECT ';' AS semi"]


@pytest.mark.parametrize(
    ("value", "configured_max", "expected"),
    [
        (None, 100, 100),
        (20, 100, 20),
        (200, 100, 100),
        (0, 100, 1),
        (-5, 100, 1),
        ("10", 100, 10),
    ],
)
def test_normalize_max_rows(value, configured_max, expected):
    assert normalize_max_rows(value, configured_max) == expected


def test_assert_readonly_select_returns_normalized_sql():
    assert assert_readonly_select(" SELECT * FROM users ; ") == "SELECT * FROM users"
