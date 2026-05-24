"""Safety checks for user-provided read-only MySQL queries."""

import re
from typing import Iterable, List, Optional, Union


class SqlSafetyError(ValueError):
    """Raised when SQL is outside this server's read-only contract."""


FORBIDDEN_PATTERNS = (
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\btruncate\b",
    r"\breplace\b",
    r"\bmerge\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bcall\b",
    r"\bset\b",
    r"\buse\b",
    r"\block\b",
    r"\bunlock\b",
    r"\banalyze\b",
    r"\boptimize\b",
    r"\brepair\b",
    r"\binto\b",
    r"\binto\s+outfile\b",
    r"\binto\s+dumpfile\b",
    r"\bload_file\s*\(",
    r"\bload\s+data\b",
    r"\blocal\s+infile\b",
    r"\bsleep\s*\(",
    r"\bbenchmark\s*\(",
    r"\bget_lock\s*\(",
    r"\brelease_lock\s*\(",
)


def normalize_max_rows(value: Optional[Union[int, str]], configured_max: int) -> int:
    """Clamp a requested row limit to the configured safety bound."""

    try:
        hard_limit = int(configured_max)
    except (TypeError, ValueError):
        hard_limit = 100
    hard_limit = max(1, hard_limit)

    if value is None:
        return hard_limit

    try:
        requested = int(value)
    except (TypeError, ValueError):
        raise SqlSafetyError("max_rows must be an integer") from None

    return min(max(1, requested), hard_limit)


def strip_sql_comments(sql: str) -> str:
    """Remove MySQL comments while preserving quoted string literals."""

    result: List[str] = []
    i = 0
    quote: Optional[str] = None
    length = len(sql)

    while i < length:
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < length else ""

        if quote:
            result.append(char)
            if char == "\\" and i + 1 < length:
                result.append(sql[i + 1])
                i += 2
                continue
            if char == quote:
                if i + 1 < length and sql[i + 1] == quote:
                    result.append(sql[i + 1])
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            result.append(char)
            i += 1
            continue

        if char == "-" and next_char == "-" and (i + 2 >= length or sql[i + 2].isspace()):
            i = _skip_until_newline(sql, i + 2)
            result.append(" ")
            continue

        if char == "#":
            i = _skip_until_newline(sql, i + 1)
            result.append(" ")
            continue

        if char == "/" and next_char == "*":
            end = sql.find("*/", i + 2)
            i = length if end == -1 else end + 2
            result.append(" ")
            continue

        result.append(char)
        i += 1

    return "".join(result)


def split_statements(sql: str) -> List[str]:
    """Split SQL on semicolons that are outside quoted strings/comments."""

    stripped = strip_sql_comments(sql)
    statements: List[str] = []
    current: List[str] = []
    quote: Optional[str] = None
    i = 0

    while i < len(stripped):
        char = stripped[i]

        if quote:
            current.append(char)
            if char == "\\" and i + 1 < len(stripped):
                current.append(stripped[i + 1])
                i += 2
                continue
            if char == quote:
                if i + 1 < len(stripped) and stripped[i + 1] == quote:
                    current.append(stripped[i + 1])
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            current.append(char)
            i += 1
            continue

        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    return statements


def validate_readonly_select(sql: str) -> str:
    """Return normalized SQL if it is one safe read-only statement."""

    if not sql or not sql.strip():
        raise SqlSafetyError("SQL must not be empty")

    statements = split_statements(sql)
    if len(statements) != 1:
        raise SqlSafetyError("Only one SQL statement is allowed")

    statement = statements[0].strip()
    searchable = _blank_quoted_literals(strip_sql_comments(statement)).lower()

    if not re.match(r"^\s*(select|with)\b", searchable):
        raise SqlSafetyError("Only SELECT or WITH ... SELECT statements are allowed")

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, searchable, flags=re.IGNORECASE):
            raise SqlSafetyError("SQL contains a forbidden operation")

    return statement.rstrip(";").strip()


def assert_readonly_select(sql: str) -> str:
    """Alias used by tool code for readable intent."""

    return validate_readonly_select(sql)


def _skip_until_newline(sql: str, start: int) -> int:
    newline = sql.find("\n", start)
    return len(sql) if newline == -1 else newline + 1


def _blank_quoted_literals(sql: str) -> str:
    """Replace quoted literal bodies with spaces before keyword scanning."""

    result: List[str] = []
    quote: Optional[str] = None
    i = 0

    while i < len(sql):
        char = sql[i]

        if quote:
            if char == "\\" and i + 1 < len(sql):
                result.extend("  ")
                i += 2
                continue
            if char == quote:
                result.append(char)
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    result.append(sql[i + 1])
                    i += 2
                    continue
                quote = None
            else:
                result.append(" ")
            i += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            result.append(char)
            i += 1
            continue

        result.append(char)
        i += 1

    return "".join(result)
