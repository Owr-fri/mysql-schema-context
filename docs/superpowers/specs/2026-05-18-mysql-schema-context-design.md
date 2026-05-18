# mysql-schema-context Skill Design

## Purpose

Create a standalone Codex skill that helps agents understand a MySQL database before writing SQL or application code. The skill should guide agents to build reliable schema context from metadata first, infer table and field meaning carefully, map entity relationships, and request user approval before inspecting business data.

## Scope

The first version focuses only on MySQL.

The skill is used when an agent needs database context before implementation, such as writing SQL, modifying data-access code, investigating business logic, or explaining how existing tables relate to a feature.

The skill does not automate live database access in v1. It provides a safe workflow, reusable MySQL discovery queries, and a structured output template.

## Proposed Structure

```text
mysql-schema-context/
  SKILL.md
  agents/openai.yaml
  references/
    mysql-discovery.md
    schema-context-template.md
```

## Skill Behavior

Agents using the skill should:

1. Identify where connection information comes from, such as user-provided credentials, environment variables, project configuration, or an existing database client.
2. Refuse to guess credentials or hard-code secrets.
3. Prefer read-only metadata inspection through MySQL system metadata.
4. Inspect tables, columns, comments, indexes, primary keys, foreign keys, and `SHOW CREATE TABLE` output before querying business data.
5. Produce an initial schema-context report from metadata.
6. Separate confirmed facts from inferred business meaning.
7. Ask the user before reading row-level data when metadata is not enough.
8. Request only limited, relevant, and preferably masked sample data after approval.
9. Avoid schema changes, writes, migrations, exports, or broad scans unless the user gives a separate explicit instruction outside this skill's default workflow.

## Safety Rules

The skill should make these rules prominent:

- Default to read-only exploration.
- Default to metadata only.
- Do not modify schema or data.
- Do not run destructive SQL.
- Do not export large datasets.
- Do not inspect sensitive fields such as passwords, tokens, secrets, identity numbers, phone numbers, emails, addresses, or payment fields unless the user explicitly approves and a masking plan is stated.
- Before sample-data access, state the reason, tables, fields, row limit, filters, and masking strategy.
- If access is unclear, pause and ask the user for permission.

## Reference Content

`references/mysql-discovery.md` should include reusable MySQL snippets for:

- Listing schemas and tables.
- Reading table and column comments.
- Reading primary keys, foreign keys, and indexes.
- Finding candidate relationships when foreign keys are absent.
- Checking enum-like columns, nullable columns, timestamp columns, and soft-delete patterns from metadata.
- Running safe sample queries only after user approval.

`references/schema-context-template.md` should include a compact report template:

- Connection and scope.
- Tables reviewed.
- Entity summary.
- Field dictionary.
- Relationship map.
- Business assumptions.
- Ambiguities and required confirmations.
- Safe query paths for the current task.

## Triggering

The frontmatter description should trigger on situations like:

- Understanding MySQL schemas before writing SQL.
- Mapping MySQL tables, fields, indexes, keys, and entity relationships.
- Inferring field meaning from database metadata.
- Asking for permission before inspecting sample data.
- Preparing database context before coding data-access behavior.

The description should start with "Use when" and avoid summarizing the full workflow.

## Validation Plan

Basic validation:

- Run the skill validation script against the generated skill folder.
- Confirm `SKILL.md` frontmatter has only `name` and `description`.
- Confirm the skill name uses lowercase letters and hyphens only.

Behavior validation:

- Test a scenario where a user asks the agent to write SQL against an unfamiliar MySQL database.
- Confirm the agent first requests connection context or uses existing safe configuration.
- Confirm the agent inspects metadata before row data.
- Confirm the agent asks permission before sample-data access.
- Confirm the output separates facts, inferences, and open questions.

## Open Decisions

- Whether to include an optional script in a later version for automated schema export.
- Whether to add PostgreSQL support as a separate skill or as a later reference file.
- Whether to keep sample-data query examples inline or move them into a dedicated safety reference if the skill grows.
