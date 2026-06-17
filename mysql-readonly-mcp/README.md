# MySQL Read-Only MCP

Python MCP server that exposes controlled MySQL schema discovery and read-only `SELECT` tools for agents.

## Tools

- `mysql_ping`
- `mysql_list_schemas`
- `mysql_list_tables`
- `mysql_describe_table(schema, table, columns=None)`
- `mysql_show_create_table`
- `mysql_list_relationships`
- `mysql_execute_select`

`mysql_execute_select` only accepts one `SELECT` or `WITH ... SELECT` statement, rejects write/DDL/file-access patterns, and enforces a row cap.

## Metadata Usage

Use `mysql_describe_table` as a table-level metadata tool. Omit `columns` to return all columns for one table in a single call, then reuse that result while reasoning about the table. Do not call `mysql_describe_table` once per column.

If only several known columns are needed, pass them together:

```json
{"schema": "app", "table": "users", "columns": ["id", "email"]}
```

Use `mysql_show_create_table` after `mysql_describe_table` when full DDL details are required, such as composite indexes, unique constraints, foreign keys, engine/options, or exact create syntax.

## Environment

Set credentials with environment variables:

```powershell
$env:MYSQL_HOST='127.0.0.1'
$env:MYSQL_PORT='3306'
$env:MYSQL_USER='readonly_user'
$env:MYSQL_PASSWORD = (Read-Host 'MySQL read-only password')
$env:MYSQL_DATABASE='app'
$env:MYSQL_MAX_ROWS='100'
```

Use a database account with read-only permissions. Do not use a privileged production account.

For multi-project use, pass `project_path` to each tool. The server will load `<project_path>/.mysql.mcp.env`. If the file is missing, the tool returns `missing_mysql_mcp_env` with a template.

## Install

```powershell
Set-Location mysql-readonly-mcp
python -m pip install -r requirements.txt
```

## Run

```powershell
Set-Location mysql-readonly-mcp
python -m mysql_readonly_mcp.server
```

When configuring an MCP client, set the server working directory to `mysql-readonly-mcp` and point the command at `python -m mysql_readonly_mcp.server` with the environment variables above.
