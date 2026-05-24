# MySQL Read-Only MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Python MCP server that gives agents real, controlled read-only access to MySQL schema metadata and safe `SELECT` queries.

**Architecture:** Keep transport, database access, SQL safety, and tool behavior separate. `server.py` exposes MCP tools, `tools.py` contains testable tool functions, `db.py` owns MySQL calls, and `sql_guard.py` enforces read-only SQL before execution.

**Tech Stack:** Python 3, official MCP Python SDK, mysql-connector-python, pytest.

---

## File Structure

- Create: `mysql-readonly-mcp/README.md`
- Create: `mysql-readonly-mcp/requirements.txt`
- Create: `mysql-readonly-mcp/mysql_readonly_mcp/__init__.py`
- Create: `mysql-readonly-mcp/mysql_readonly_mcp/config.py`
- Create: `mysql-readonly-mcp/mysql_readonly_mcp/sql_guard.py`
- Create: `mysql-readonly-mcp/mysql_readonly_mcp/db.py`
- Create: `mysql-readonly-mcp/mysql_readonly_mcp/tools.py`
- Create: `mysql-readonly-mcp/mysql_readonly_mcp/server.py`
- Create: `mysql-readonly-mcp/tests/test_sql_guard.py`
- Create: `mysql-readonly-mcp/tests/test_tools_safety.py`
- Modify: `mysql-schema-context/SKILL.md`
- Modify: `mysql-schema-context/README.md`

## Task 1: SQL Guard Tests

- [ ] Write failing tests in `mysql-readonly-mcp/tests/test_sql_guard.py` for safe `SELECT`, safe CTE, empty SQL, multi-statements, writes, DDL, `INTO OUTFILE`, `LOAD_FILE`, and max row normalization.
- [ ] Run `python -m pytest mysql-readonly-mcp/tests/test_sql_guard.py -q`; expected: fail because module does not exist.

## Task 2: SQL Guard Implementation

- [ ] Implement `mysql_readonly_mcp/sql_guard.py` with `SqlSafetyError`, `normalize_max_rows`, `strip_sql_comments`, `split_statements`, `validate_readonly_select`, and `assert_readonly_select`.
- [ ] Run `python -m pytest mysql-readonly-mcp/tests/test_sql_guard.py -q`; expected: pass.

## Task 3: Config and Database Layer

- [ ] Implement `config.py` to load env-based settings without exposing secrets.
- [ ] Implement `db.py` with safe identifier quoting, connection creation, metadata queries, `show_create_table`, and capped query execution.
- [ ] Keep imports of `mysql.connector` inside DB code so SQL guard tests do not require MySQL dependencies.

## Task 4: Tool Functions and Tests

- [ ] Write `mysql-readonly-mcp/tests/test_tools_safety.py` with a fake DB object proving `mysql_execute_select` rejects unsafe SQL before DB execution and caps max rows.
- [ ] Implement `tools.py` with `MySQLTools` class and methods matching the MCP tools.
- [ ] Run `python -m pytest mysql-readonly-mcp/tests/test_sql_guard.py mysql-readonly-mcp/tests/test_tools_safety.py -q`; expected: pass.

## Task 5: MCP Server Wrapper

- [ ] Implement `server.py` using the official MCP Python SDK `FastMCP`.
- [ ] Expose `mysql_ping`, `mysql_list_schemas`, `mysql_list_tables`, `mysql_describe_table`, `mysql_show_create_table`, `mysql_list_relationships`, and `mysql_execute_select`.
- [ ] Add `requirements.txt` with `mcp` and `mysql-connector-python`.
- [ ] Add README usage and Codex MCP configuration example.

## Task 6: Skill Integration

- [ ] Update `mysql-schema-context/SKILL.md` to prefer MCP tools when available.
- [ ] Keep metadata-first workflow and permission gate.
- [ ] Update `mysql-schema-context/README.md` to describe the companion MCP server.

## Task 7: Verification

- [ ] Run unit tests.
- [ ] Run static content checks for TODOs, non-ASCII, hard-coded secrets, and unsafe SQL wording.
- [ ] If dependencies are missing, report the exact missing dependency and the command to install it; do not install without approval.
