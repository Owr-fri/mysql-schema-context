# MySQL Discovery Reference

## Metadata First

Use these queries before row-level data access. Replace `:schema_name` and other parameters with properly quoted values for the active MySQL client.

## Schemas and Tables

```sql
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;
```

```sql
SELECT table_name, table_type, table_rows, table_comment
FROM information_schema.tables
WHERE table_schema = :schema_name
ORDER BY table_name;
```

## Columns and Comments

```sql
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
WHERE table_schema = :schema_name
ORDER BY table_name, ordinal_position;
```

## Primary Keys, Foreign Keys, and Indexes

```sql
SELECT
  table_name,
  constraint_name,
  constraint_type
FROM information_schema.table_constraints
WHERE table_schema = :schema_name
ORDER BY table_name, constraint_type, constraint_name;
```

```sql
SELECT
  table_name,
  column_name,
  referenced_table_name,
  referenced_column_name,
  constraint_name
FROM information_schema.key_column_usage
WHERE table_schema = :schema_name
  AND referenced_table_name IS NOT NULL
ORDER BY table_name, column_name;
```

```sql
SELECT
  table_name,
  index_name,
  non_unique,
  seq_in_index,
  column_name,
  index_type
FROM information_schema.statistics
WHERE table_schema = :schema_name
ORDER BY table_name, index_name, seq_in_index;
```

## Table DDL

```sql
SHOW CREATE TABLE `table_name`;
```

Use DDL to inspect generated columns, enum values, constraints, comments, charset, and storage details that may be easier to understand together.

## Candidate Relationships without Foreign Keys

Look for:

- Columns ending in `_id`, `_no`, `_code`, or `_uuid`.
- Indexed columns with names matching another table's primary or unique key.
- Join tables with two or more indexed foreign-key-like columns.
- Audit fields such as `created_by`, `updated_by`, `deleted_by`.
- Status/history tables with parent identifiers and timestamp columns.

Treat these as inferred relationships until confirmed.

## Metadata Clues for Business Meaning

- `enum` and `set` values can reveal status domains.
- `tinyint(1)` may be a boolean flag, but confirm with names and comments.
- `deleted_at`, `is_deleted`, and `delete_time` often indicate soft delete.
- `created_at`, `updated_at`, `create_time`, and `update_time` usually identify lifecycle timestamps.
- `tenant_id`, `org_id`, and `company_id` often define data partitioning.
- Nullable columns can signal optional workflow states.

## Sample Data Only after Approval

Never start with `SELECT *`. After approval, use narrow projections:

```sql
SELECT
  id,
  status,
  type,
  created_at
FROM `table_name`
WHERE created_at >= CURRENT_DATE - INTERVAL 30 DAY
ORDER BY created_at DESC
LIMIT 20;
```

For sensitive fields, exclude them or mask them:

```sql
SELECT
  id,
  CONCAT(LEFT(email, 2), '***') AS masked_email,
  status,
  created_at
FROM `user_table`
LIMIT 10;
```
