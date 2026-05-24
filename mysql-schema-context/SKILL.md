---
name: mysql-schema-context
description: Use when working with MySQL schemas before writing SQL or data-access code, mapping tables, columns, keys, indexes, entity relationships, inferring field meaning from metadata, or deciding whether sample data access needs user approval
---

# MySQL Schema Context

## Overview

Build database understanding before writing SQL or code. Prefer the companion MySQL MCP tools when available, start from MySQL metadata, separate facts from inference, and ask before reading business data.

## Tool Preference

If the `mysql-readonly` MCP server is available, use its tools instead of hand-written discovery SQL:

1. Call `mysql_ping` to verify connectivity.
2. Call `mysql_list_schemas` and `mysql_list_tables` to find scope.
3. Call `mysql_describe_table`, `mysql_show_create_table`, and `mysql_list_relationships` before writing SQL or code.
4. Use `mysql_execute_select` only after metadata is insufficient and row-level access is appropriate for the task.

If MCP tools are unavailable, use `references/mysql-discovery.md` to guide manual read-only discovery through the available database client.

## Core Rules

- Default to read-only exploration.
- Default to metadata only.
- Do not guess credentials, table structures, or field meanings as facts.
- Do not modify schema or data.
- Do not run destructive SQL.
- Do not export large datasets.
- Do not inspect sensitive fields unless the user explicitly approves a masking plan.

Sensitive fields include passwords, tokens, secrets, identity numbers, phone numbers, emails, addresses, payment details, and authentication material.

## Workflow

1. Identify the task and the MySQL scope: database/schema name, relevant feature, known tables, and available connection path.
2. Confirm credentials come from the user, environment variables, project configuration, or an existing database client. Never hard-code secrets.
3. Inspect metadata first with MCP tools or manual metadata SQL: schemas, tables, columns, comments, indexes, primary keys, foreign keys, and `SHOW CREATE TABLE`.
4. Build an initial schema-context report using `references/schema-context-template.md`.
5. Mark each conclusion as fact, inference, or unknown.
6. If field meaning or relationships remain unclear, request permission before sample-data access.
7. After approval, query only the approved tables and columns with narrow filters, low row limits, and masking for sensitive values. Prefer `mysql_execute_select` so read-only and row-cap rules are enforced by the MCP server.
8. Use the final context to write SQL, code, or explanations.

## Permission Gate for Sample Data

Before querying row-level data, ask the user with:

- Why metadata is insufficient.
- Which tables and columns are needed.
- The proposed filters and row limit.
- Which fields will be excluded or masked.
- Whether the query is read-only.

Do not proceed until the user approves.

## References

- Use `references/mysql-discovery.md` for MySQL metadata queries and safe sample-data patterns.
- Use `references/schema-context-template.md` for the output report format.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Writing SQL against invented table names | Inspect metadata or ask for schema first |
| Treating guessed field meanings as facts | Label them as inference and list confirmation needed |
| Running `SELECT * LIMIT 5` on business tables | Ask permission and select only approved non-sensitive fields |
| Ignoring comments and constraints | Check comments, keys, indexes, and `SHOW CREATE TABLE` first |
| Assuming absent foreign keys mean no relationships | Look for naming patterns, unique keys, indexes, and join tables |
