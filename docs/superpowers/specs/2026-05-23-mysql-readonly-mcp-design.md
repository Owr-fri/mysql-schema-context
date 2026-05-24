# MySQL Read-Only MCP Design

## Purpose

Add a real tool layer for the `mysql-schema-context` skill. The skill teaches the agent when and how to inspect MySQL; the MCP server provides controlled database access so the agent can actually discover schemas, tables, fields, relationships, and run read-only `SELECT` queries.

## Scope

Build a Python MCP server for MySQL with read-only behavior. The first version supports:

- Connection checks.
- Schema and table discovery.
- Column, key, index, and relationship discovery.
- `SHOW CREATE TABLE`.
- Arbitrary single-statement read-only `SELECT` and `WITH ... SELECT` queries with row caps.

The server does not support writes, migrations, exports, file reads, imports, or multi-statement execution.

## Architecture

```text
mysql-readonly-mcp/
  README.md
  requirements.txt
  mysql_readonly_mcp/
    __init__.py
    config.py
    db.py
    sql_guard.py
    tools.py
    server.py
  tests/
    test_sql_guard.py
    test_tools_safety.py
```

Responsibilities:

- `config.py`: read MySQL connection settings and safety limits from environment variables.
- `sql_guard.py`: enforce single-statement, read-only SQL before any arbitrary query is executed.
- `db.py`: open MySQL connections, run parameterized metadata queries, quote safe identifiers, and cap rows.
- `tools.py`: implement tool behavior independent from MCP transport so it can be unit-tested.
- `server.py`: expose tools through the MCP Python SDK.

## Environment Configuration

Use environment variables instead of hard-coded credentials:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE` optional default schema
- `MYSQL_CONNECT_TIMEOUT` default `5`
- `MYSQL_MAX_ROWS` default `100`

The server should not log or return passwords.

## MCP Tools

- `mysql_ping()`: verify connection with `SELECT 1`.
- `mysql_list_schemas(include_system: bool = false)`: list schemas.
- `mysql_list_tables(schema: str)`: list tables, types, approximate row counts, and comments.
- `mysql_describe_table(schema: str, table: str)`: return columns and comments.
- `mysql_show_create_table(schema: str, table: str)`: return DDL for one table.
- `mysql_list_relationships(schema: str)`: return primary keys, foreign keys, indexes, and candidate relationships inferred from metadata.
- `mysql_execute_select(sql: str, max_rows: int | None = None)`: run one read-only `SELECT` or `WITH ... SELECT`, capped by configured maximum rows.

## SQL Safety Rules

`mysql_execute_select` must reject:

- Empty SQL.
- Multiple statements.
- Statements not starting with `SELECT` or `WITH`.
- Comments or string tricks that hide a second statement.
- Write or DDL keywords such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `MERGE`, `GRANT`, `REVOKE`, `CALL`, `SET`, `USE`, `LOCK`, `UNLOCK`, `ANALYZE`, `OPTIMIZE`, `REPAIR`.
- Export/import/file access patterns such as `INTO OUTFILE`, `INTO DUMPFILE`, `LOAD_FILE`, `LOAD DATA`, `LOCAL INFILE`.

The server should fetch at most `max_rows + 1` rows and report `truncated: true` when results exceed the cap.

## Skill Integration

Update `mysql-schema-context/SKILL.md` so agents:

- Prefer MCP tools when available.
- Use metadata tools before arbitrary `mysql_execute_select`.
- Use `mysql_execute_select` only for read-only clarification and sample queries.
- Continue to separate facts, inferences, and unknowns.
- Continue to request user approval before row-level sample data when the task involves sensitive or business data.

## Validation

Unit tests should cover:

- Accepting safe `SELECT` and `WITH ... SELECT`.
- Rejecting writes, DDL, multi-statements, and file export/import patterns.
- Enforcing row cap bounds.
- Tool safety wrappers rejecting unsafe SQL before database execution.

Manual checks should cover:

- Required files exist.
- `SKILL.md` references MCP usage.
- No secrets are hard-coded.
- MCP server imports or fails with a clear missing-dependency message.
