# Project Environment MySQL MCP Design

## Purpose

Make the MySQL read-only MCP server reusable across many projects. The agent should be able to call the MCP from any project, pass that project's root path, and let the MCP load that project's database connection settings from a project-local env file.

This keeps the MCP server generic while making database context discovery practical for the `mysql-schema-context` skill.

## Goals

- Let every MySQL MCP tool accept the active project root path.
- Load database settings from `<project_path>/.mysql.mcp.env`.
- Return a clear, structured missing-configuration response when that file does not exist.
- Update the skill so agents pass the current project path to MCP tools.
- Update the skill so agents generate a safe `.mysql.mcp.env` template when configuration is missing.
- Avoid hard-coded credentials and avoid writing real secrets automatically.

## Non-Goals

- Do not automatically read arbitrary application `.env` files by default.
- Do not persist project selection in server-global mutable state.
- Do not add write-capable database tools.
- Do not infer or guess database credentials.

## Architecture

Current MCP startup loads one `MySQLConfig` from process environment in `server.py`, then shares one `MySQLTools` instance for all requests. That makes the connection fixed for the lifetime of the MCP process.

The new design moves configuration resolution to tool-call time:

```text
agent has current project path
-> agent calls mysql_list_tables(schema, project_path)
-> MCP resolves <project_path>/.mysql.mcp.env
-> MCP builds MySQLConfig
-> MCP creates MySQLDatabase/MySQLTools for the request
-> MCP executes read-only metadata or SELECT behavior
```

Each tool should accept:

```python
project_path: str | None = None
```

The project path should be required for project-local env loading. If it is omitted, the MCP may fall back to existing process environment behavior for backward compatibility, but skill-guided usage should always pass it.

## Env File

The project-local env file is:

```text
<project_path>/.mysql.mcp.env
```

Template:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=readonly_user
MYSQL_PASSWORD=
MYSQL_DATABASE=
MYSQL_CONNECT_TIMEOUT=5
MYSQL_MAX_ROWS=100
```

The parser should support simple `KEY=value` lines, blank lines, and `#` comments. It should not need shell expansion or complex dotenv syntax for v1.

Process environment variables may override values loaded from `.mysql.mcp.env`. This lets advanced users keep secrets outside the repo while still using project-local defaults.

## Missing Configuration Behavior

When `project_path` is provided and `<project_path>/.mysql.mcp.env` does not exist, MCP tools should return a structured response instead of attempting a database connection:

```json
{
  "error": "missing_mysql_mcp_env",
  "project_path": "E:\\code\\some_project",
  "expected_file": "E:\\code\\some_project\\.mysql.mcp.env",
  "required_keys": [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD"
  ],
  "template": "MYSQL_HOST=127.0.0.1\nMYSQL_PORT=3306\n..."
}
```

This response is intended for the agent and skill workflow. The agent should stop database discovery, create or suggest the template, and ask the user to fill in the connection details.

## Skill Integration

Update `mysql-schema-context/SKILL.md` so agents:

- Pass the current project root as `project_path` on every MySQL MCP tool call.
- Treat `missing_mysql_mcp_env` as an actionable setup step, not a database failure.
- Create `<project_path>/.mysql.mcp.env` from the MCP-provided template or the skill's documented template.
- Ensure `.mysql.mcp.env` is ignored by git, adding it to `.gitignore` if needed.
- Tell the user to fill in a read-only database account and rerun the MCP query.
- Never write real passwords or privileged production credentials into the file on the user's behalf.

## Error Handling

- Invalid `project_path`: return a structured `invalid_project_path` error.
- Missing env file: return `missing_mysql_mcp_env`.
- Missing required values in the env file: return `incomplete_mysql_mcp_env` with the missing keys.
- Invalid integer values: keep current default behavior for optional integer settings, but report invalid required values if any are introduced later.
- Database connection errors: return the existing tool error behavior without exposing passwords.

## Testing

Add focused tests for:

- Loading config from `.mysql.mcp.env`.
- Environment variables overriding env-file values.
- Missing env file returning `missing_mysql_mcp_env`.
- Missing required env values returning `incomplete_mysql_mcp_env`.
- Tool wrappers passing `project_path` into per-call config resolution.
- Skill text requiring `project_path` and missing-env setup behavior.

Manual validation:

- Run existing SQL safety tests.
- Run MCP import/startup check.
- Confirm no secrets are logged, returned, or committed.
