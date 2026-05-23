# Project Env MySQL MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the MySQL read-only MCP server load database connection settings from each caller project's `.mysql.mcp.env` file when the agent passes `project_path`.

**Architecture:** Move MySQL config resolution from MCP startup to tool-call time. Add a small env-file parser and structured configuration errors in `config.py`, then update `server.py` so every MCP tool accepts `project_path` and creates request-local `MySQLTools`. Update the skill documentation so agents always pass the active project root and guide users through missing config setup.

**Tech Stack:** Python, MCP FastMCP, pytest, MySQL connector, Markdown skill docs.

---

## File Structure

- Modify `mysql-readonly-mcp/mysql_readonly_mcp/config.py`: parse project-local `.mysql.mcp.env`, merge process environment overrides, validate required key presence, and expose structured config errors.
- Modify `mysql-readonly-mcp/mysql_readonly_mcp/server.py`: build request-local tools for each MCP call and add `project_path` arguments.
- Create `mysql-readonly-mcp/tests/test_config.py`: config parsing, missing-file, invalid-path, required-key, and override tests.
- Create `mysql-readonly-mcp/tests/test_server_project_config.py`: server wrapper behavior without needing a real MySQL connection.
- Modify `mysql-schema-context/SKILL.md`: document `project_path`, missing-env setup, `.gitignore`, and safe template behavior.
- Create `mysql-schema-context/tests/test_skill_project_env.py` if no existing skill-doc tests exist: lightweight text assertions for the new required workflow.

## Task 1: Add Project Env Config Tests

**Files:**
- Create: `mysql-readonly-mcp/tests/test_config.py`
- Modify later: `mysql-readonly-mcp/mysql_readonly_mcp/config.py`

- [ ] **Step 1: Write failing tests for env-file loading**

Create `mysql-readonly-mcp/tests/test_config.py`:

```python
from pathlib import Path

import pytest

from mysql_readonly_mcp.config import (
    ConfigResolutionError,
    ENV_FILE_NAME,
    load_config,
)


def write_env(project: Path, content: str):
    project.mkdir()
    (project / ENV_FILE_NAME).write_text(content, encoding="utf-8")


def test_load_config_reads_project_env_file(tmp_path, monkeypatch):
    project = tmp_path / "app"
    write_env(
        project,
        """
        # local database for agent schema discovery
        MYSQL_HOST=localhost
        MYSQL_PORT=3307
        MYSQL_USER=readonly
        MYSQL_PASSWORD=
        MYSQL_DATABASE=shop
        MYSQL_CONNECT_TIMEOUT=9
        MYSQL_MAX_ROWS=25
        """,
    )
    for key in [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
        "MYSQL_CONNECT_TIMEOUT",
        "MYSQL_MAX_ROWS",
    ]:
        monkeypatch.delenv(key, raising=False)

    config = load_config(project_path=str(project))

    assert config.host == "localhost"
    assert config.port == 3307
    assert config.user == "readonly"
    assert config.password == ""
    assert config.database == "shop"
    assert config.connect_timeout == 9
    assert config.max_rows == 25
```

- [ ] **Step 2: Write failing tests for overrides and structured errors**

Append:

```python
def test_process_environment_overrides_project_env_file(tmp_path, monkeypatch):
    project = tmp_path / "app"
    write_env(
        project,
        """
        MYSQL_HOST=file-host
        MYSQL_PORT=3306
        MYSQL_USER=file-user
        MYSQL_PASSWORD=file-pass
        """,
    )
    for key in [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
        "MYSQL_CONNECT_TIMEOUT",
        "MYSQL_MAX_ROWS",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MYSQL_HOST", "env-host")
    monkeypatch.setenv("MYSQL_PASSWORD", "env-pass")

    config = load_config(project_path=str(project))

    assert config.host == "env-host"
    assert config.user == "file-user"
    assert config.password == "env-pass"


def test_missing_project_env_returns_structured_error(tmp_path):
    project = tmp_path / "app"
    project.mkdir()

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(project))

    payload = exc_info.value.to_response()
    assert payload["error"] == "missing_mysql_mcp_env"
    assert payload["project_path"] == str(project.resolve())
    assert payload["expected_file"] == str(project.resolve() / ENV_FILE_NAME)
    assert "MYSQL_HOST=127.0.0.1" in payload["template"]


def test_invalid_project_path_returns_structured_error(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(missing))

    assert exc_info.value.to_response()["error"] == "invalid_project_path"


def test_missing_required_key_returns_structured_error(tmp_path):
    project = tmp_path / "app"
    write_env(
        project,
        """
        MYSQL_HOST=127.0.0.1
        MYSQL_PORT=3306
        MYSQL_USER=readonly
        """,
    )

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(project))

    payload = exc_info.value.to_response()
    assert payload["error"] == "incomplete_mysql_mcp_env"
    assert payload["missing_keys"] == ["MYSQL_PASSWORD"]
```

- [ ] **Step 3: Run tests and verify they fail**

Run from `mysql-readonly-mcp`:

```powershell
python -m pytest tests/test_config.py -q
```

Expected: FAIL because `ConfigResolutionError`, `ENV_FILE_NAME`, and `load_config(project_path=...)` do not exist yet.

- [ ] **Step 4: Commit failing tests**

```powershell
git add mysql-readonly-mcp/tests/test_config.py
git commit -m "test: cover project env mysql config loading"
```

## Task 2: Implement Project Env Config Resolution

**Files:**
- Modify: `mysql-readonly-mcp/mysql_readonly_mcp/config.py`
- Test: `mysql-readonly-mcp/tests/test_config.py`

- [ ] **Step 1: Add constants and structured error type**

In `config.py`, add:

```python
from pathlib import Path

ENV_FILE_NAME = ".mysql.mcp.env"
REQUIRED_ENV_KEYS = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD")
ENV_TEMPLATE = """MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=readonly_user
MYSQL_PASSWORD=
MYSQL_DATABASE=
MYSQL_CONNECT_TIMEOUT=5
MYSQL_MAX_ROWS=100
"""


class ConfigResolutionError(Exception):
    def __init__(self, payload):
        super().__init__(payload.get("error", "config_resolution_error"))
        self.payload = payload

    def to_response(self):
        return dict(self.payload)
```

- [ ] **Step 2: Add env-file parser and project resolver**

Add focused helpers:

```python
def _resolve_project_path(project_path: str) -> Path:
    path = Path(project_path).expanduser().resolve()
    if not path.is_dir():
        raise ConfigResolutionError({"error": "invalid_project_path", "project_path": str(path)})
    return path


def _parse_env_file(path: Path) -> dict:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values
```

- [ ] **Step 3: Update `load_config` with project-path behavior**

Replace `load_config()` with a version that accepts `project_path: str = None`:

```python
def load_config(project_path: str = None) -> MySQLConfig:
    values = {}
    if project_path:
        root = _resolve_project_path(project_path)
        env_file = root / ENV_FILE_NAME
        if not env_file.exists():
            raise ConfigResolutionError(
                {
                    "error": "missing_mysql_mcp_env",
                    "project_path": str(root),
                    "expected_file": str(env_file),
                    "required_keys": list(REQUIRED_ENV_KEYS),
                    "template": ENV_TEMPLATE,
                }
            )
        values.update(_parse_env_file(env_file))
        missing = [key for key in REQUIRED_ENV_KEYS if key not in values and key not in os.environ]
        if missing:
            raise ConfigResolutionError(
                {
                    "error": "incomplete_mysql_mcp_env",
                    "project_path": str(root),
                    "expected_file": str(env_file),
                    "missing_keys": missing,
                    "required_keys": list(REQUIRED_ENV_KEYS),
                    "template": ENV_TEMPLATE,
                }
            )

    return MySQLConfig(
        host=_value(values, "MYSQL_HOST", "127.0.0.1"),
        port=_int_value(values, "MYSQL_PORT", 3306),
        user=_value(values, "MYSQL_USER", ""),
        password=_value(values, "MYSQL_PASSWORD", ""),
        database=_value(values, "MYSQL_DATABASE", ""),
        connect_timeout=_int_value(values, "MYSQL_CONNECT_TIMEOUT", 5),
        max_rows=max(1, _int_value(values, "MYSQL_MAX_ROWS", 100)),
    )
```

Add:

```python
def _value(values: dict, name: str, default: str) -> str:
    return os.environ.get(name, values.get(name, default))


def _int_value(values: dict, name: str, default: int) -> int:
    value = _value(values, name, "")
    if value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default
```

Remove `_int_env` if it becomes unused.

- [ ] **Step 4: Run config tests**

Run:

```powershell
Set-Location mysql-readonly-mcp
python -m pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Run existing safety tests**

Run:

```powershell
Set-Location mysql-readonly-mcp
python -m pytest tests/test_sql_guard.py tests/test_tools_safety.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit implementation**

```powershell
git add mysql-readonly-mcp/mysql_readonly_mcp/config.py
git commit -m "feat: load mysql mcp config from project env"
```

## Task 3: Move MCP Server Config to Tool-Call Time

**Files:**
- Create: `mysql-readonly-mcp/tests/test_server_project_config.py`
- Modify: `mysql-readonly-mcp/mysql_readonly_mcp/server.py`

- [ ] **Step 1: Write failing server wrapper tests**

Create `mysql-readonly-mcp/tests/test_server_project_config.py`:

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mysql_readonly_mcp.server as server


class FakeTools:
    def __init__(self):
        self.calls = []

    def mysql_ping(self):
        return {"ok": True}

    def mysql_list_tables(self, schema):
        self.calls.append(("mysql_list_tables", schema))
        return [{"table_name": "users"}]


def test_with_tools_returns_config_error_payload(monkeypatch):
    class FakeConfigError(Exception):
        def to_response(self):
            return {"error": "missing_mysql_mcp_env"}

    def fake_load_config(project_path=None):
        raise FakeConfigError()

    monkeypatch.setattr(server, "ConfigResolutionError", FakeConfigError)
    monkeypatch.setattr(server, "load_config", fake_load_config)

    result = server._with_tools("E:/app", lambda tools: tools.mysql_ping())

    assert result == {"error": "missing_mysql_mcp_env"}


def test_with_tools_builds_tools_per_project(monkeypatch):
    seen = {}

    def fake_load_config(project_path=None):
        seen["project_path"] = project_path
        return type("Config", (), {"max_rows": 33})()

    class FakeDB:
        def __init__(self, config):
            self.config = config

    def fake_tools(db, configured_max_rows):
        seen["configured_max_rows"] = configured_max_rows
        return FakeTools()

    monkeypatch.setattr(server, "load_config", fake_load_config)
    monkeypatch.setattr(server, "MySQLDatabase", FakeDB)
    monkeypatch.setattr(server, "MySQLTools", fake_tools)

    result = server._with_tools("E:/app", lambda tools: tools.mysql_list_tables("shop"))

    assert seen == {"project_path": "E:/app", "configured_max_rows": 33}
    assert result == [{"table_name": "users"}]
```

- [ ] **Step 2: Run server tests and verify they fail**

Run:

```powershell
Set-Location mysql-readonly-mcp
python -m pytest tests/test_server_project_config.py -q
```

Expected: FAIL because `server._with_tools` and imported `ConfigResolutionError` do not exist.

- [ ] **Step 3: Update `server.py` imports and helper**

Modify imports:

```python
from .config import ConfigResolutionError, load_config
```

Add above `build_server()`:

```python
def _build_tools(project_path: str = None):
    config = load_config(project_path=project_path)
    return MySQLTools(MySQLDatabase(config), configured_max_rows=config.max_rows)


def _with_tools(project_path: str = None, operation=None):
    try:
        tools = _build_tools(project_path=project_path)
        return operation(tools)
    except ConfigResolutionError as exc:
        return exc.to_response()
```

- [ ] **Step 4: Update all MCP tool signatures**

Inside `build_server()`, remove startup-time `config = ...` and shared `tools = ...`.

Update tools:

```python
@mcp.tool()
def mysql_ping(project_path: str = None):
    return _with_tools(project_path, lambda tools: tools.mysql_ping())


@mcp.tool()
def mysql_list_schemas(include_system: bool = False, project_path: str = None):
    return _with_tools(project_path, lambda tools: tools.mysql_list_schemas(include_system=include_system))


@mcp.tool()
def mysql_list_tables(schema: str, project_path: str = None):
    return _with_tools(project_path, lambda tools: tools.mysql_list_tables(schema))
```

Apply the same pattern to:

- `mysql_describe_table(schema, table, project_path=None)`
- `mysql_show_create_table(schema, table, project_path=None)`
- `mysql_list_relationships(schema, project_path=None)`
- `mysql_execute_select(sql, max_rows=None, project_path=None)`

- [ ] **Step 5: Run server and existing tests**

Run:

```powershell
Set-Location mysql-readonly-mcp
python -m pytest tests/test_server_project_config.py tests/test_config.py tests/test_sql_guard.py tests/test_tools_safety.py -q
```

Expected: PASS.

- [ ] **Step 6: Run import/startup check**

Run:

```powershell
Set-Location mysql-readonly-mcp
python -c "from mysql_readonly_mcp.server import build_server; build_server(); print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 7: Commit server changes**

```powershell
git add mysql-readonly-mcp/mysql_readonly_mcp/server.py mysql-readonly-mcp/tests/test_server_project_config.py
git commit -m "feat: resolve mysql mcp config per tool call"
```

## Task 4: Update Skill Workflow for Project Env Setup

**Files:**
- Modify: `mysql-schema-context/SKILL.md`
- Create: `mysql-schema-context/tests/test_skill_project_env.py`

- [ ] **Step 1: Write failing skill documentation tests**

Create `mysql-schema-context/tests/test_skill_project_env.py`:

```python
from pathlib import Path


def test_skill_requires_project_path_for_mcp_tools():
    skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    text = skill.read_text(encoding="utf-8")

    assert "project_path" in text
    assert "current project root" in text
    assert ".mysql.mcp.env" in text
    assert "missing_mysql_mcp_env" in text
    assert ".gitignore" in text
```

- [ ] **Step 2: Run skill doc test and verify it fails**

Run from repository root:

```powershell
python -m pytest mysql-schema-context/tests/test_skill_project_env.py -q
```

Expected: FAIL because the skill does not mention the project env workflow yet.

- [ ] **Step 3: Update `SKILL.md` Tool Preference section**

Change the MCP workflow to require project path:

```markdown
When calling MySQL MCP tools, pass the current project root as `project_path` on every call. The MCP uses this to load `<project_path>/.mysql.mcp.env`.

1. Call `mysql_ping(project_path=current_project_root)` to verify connectivity.
2. Call `mysql_list_schemas(project_path=current_project_root)` and `mysql_list_tables(schema, project_path=current_project_root)` to find scope.
3. Call `mysql_describe_table`, `mysql_show_create_table`, and `mysql_list_relationships` with the same `project_path` before writing SQL or code.
4. Use `mysql_execute_select(sql, max_rows, project_path=current_project_root)` only after metadata is insufficient and row-level access is appropriate for the task.
```

- [ ] **Step 4: Add missing-env setup instructions**

Add a new section:

```text
## Project MCP Configuration

If a MySQL MCP tool returns `missing_mysql_mcp_env`, stop database discovery and help the user create `<current project root>/.mysql.mcp.env`.

Use this template:

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=readonly_user
MYSQL_PASSWORD=
MYSQL_DATABASE=
MYSQL_CONNECT_TIMEOUT=5
MYSQL_MAX_ROWS=100

Do not fill in real passwords for the user. Tell the user to use a read-only database account and rerun the MCP query after the file is complete.

Ensure `.mysql.mcp.env` is ignored by git. If the current project has a `.gitignore`, add `.mysql.mcp.env` if it is missing.
```

- [ ] **Step 5: Run skill doc test**

Run:

```powershell
python -m pytest mysql-schema-context/tests/test_skill_project_env.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit skill update**

```powershell
git add mysql-schema-context/SKILL.md mysql-schema-context/tests/test_skill_project_env.py
git commit -m "docs: teach mysql skill project env setup"
```

## Task 5: Final Verification and Documentation Check

**Files:**
- Modify if needed: `mysql-readonly-mcp/README.md`
- Verify: all changed files

- [ ] **Step 1: Update README if needed**

If `mysql-readonly-mcp/README.md` still only documents process environment variables, add a short MCP-client section:

```markdown
For multi-project use, pass `project_path` to each tool. The server will load `<project_path>/.mysql.mcp.env`. If the file is missing, the tool returns `missing_mysql_mcp_env` with a template.
```

- [ ] **Step 2: Run the full test suite**

Run:

```powershell
Set-Location mysql-readonly-mcp
python -m pytest tests -q
```

Expected: PASS.

Run from repository root:

```powershell
python -m pytest mysql-schema-context/tests -q
```

Expected: PASS.

- [ ] **Step 3: Verify no secrets are committed**

Run:

```powershell
git -c safe.directory=E:/code/Python/sql_table_skill diff --cached
git -c safe.directory=E:/code/Python/sql_table_skill diff
```

Expected: diffs contain templates and placeholders only; no real host/password beyond examples.

- [ ] **Step 4: Check git status**

Run:

```powershell
git -c safe.directory=E:/code/Python/sql_table_skill status --short
```

Expected: only intentional files changed or untracked. Do not revert unrelated pre-existing untracked files.

- [ ] **Step 5: Final commit**

If README changed:

```powershell
git add mysql-readonly-mcp/README.md
git commit -m "docs: document project env mysql mcp usage"
```

If README did not need changes, skip this commit.
