from pathlib import Path
import sys
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mysql_readonly_mcp.config import (
    ConfigResolutionError,
    load_config,
)  # noqa: E402


PROJECT_ENV_FILE = ".mysql.mcp.env"
MYSQL_ENV_KEYS = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
    "MYSQL_CONNECT_TIMEOUT",
    "MYSQL_MAX_ROWS",
]


def clear_mysql_env(monkeypatch):
    for key in MYSQL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def write_env(project: Path, content: str):
    project.mkdir()
    (project / PROJECT_ENV_FILE).write_text(dedent(content).lstrip(), encoding="utf-8")


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
    clear_mysql_env(monkeypatch)

    config = load_config(project_path=str(project))

    assert config.host == "localhost"
    assert config.port == 3307
    assert config.user == "readonly"
    assert config.password == ""
    assert config.database == "shop"
    assert config.connect_timeout == 9
    assert config.max_rows == 25


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
    clear_mysql_env(monkeypatch)
    monkeypatch.setenv("MYSQL_HOST", "env-host")
    monkeypatch.setenv("MYSQL_PASSWORD", "env-pass")

    config = load_config(project_path=str(project))

    assert config.host == "env-host"
    assert config.user == "file-user"
    assert config.password == "env-pass"


def test_missing_project_env_returns_structured_error(tmp_path, monkeypatch):
    project = tmp_path / "app"
    project.mkdir()
    clear_mysql_env(monkeypatch)

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(project))

    payload = exc_info.value.to_response()
    assert payload["error"] == "missing_mysql_mcp_env"
    assert payload["project_path"] == str(project.resolve())
    assert payload["expected_file"] == str(project.resolve() / PROJECT_ENV_FILE)
    assert "MYSQL_HOST=127.0.0.1" in payload["template"]


def test_invalid_project_path_returns_structured_error(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    clear_mysql_env(monkeypatch)

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(missing))

    assert exc_info.value.to_response()["error"] == "invalid_project_path"


def test_missing_required_key_returns_structured_error(tmp_path, monkeypatch):
    project = tmp_path / "app"
    write_env(
        project,
        """
        MYSQL_HOST=127.0.0.1
        MYSQL_PORT=3306
        MYSQL_USER=readonly
        """,
    )
    clear_mysql_env(monkeypatch)

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(project))

    payload = exc_info.value.to_response()
    assert payload["error"] == "incomplete_mysql_mcp_env"
    assert payload["missing_keys"] == ["MYSQL_PASSWORD"]


def test_blank_required_project_values_return_structured_error(tmp_path, monkeypatch):
    clear_mysql_env(monkeypatch)
    project = tmp_path / "app"
    write_env(
        project,
        """
        MYSQL_HOST=
        MYSQL_PORT=
        MYSQL_USER=
        MYSQL_PASSWORD=
        """,
    )

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(project))

    payload = exc_info.value.to_response()
    assert payload["error"] == "incomplete_mysql_mcp_env"
    assert payload["missing_keys"] == ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER"]


def test_invalid_required_project_port_returns_structured_error(
    tmp_path, monkeypatch
):
    clear_mysql_env(monkeypatch)
    project = tmp_path / "app"
    write_env(
        project,
        """
        MYSQL_HOST=127.0.0.1
        MYSQL_PORT=not-a-port
        MYSQL_USER=readonly
        MYSQL_PASSWORD=
        """,
    )

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(project))

    payload = exc_info.value.to_response()
    assert payload["error"] == "incomplete_mysql_mcp_env"
    assert payload["missing_keys"] == ["MYSQL_PORT"]


def test_invalid_required_port_from_environment_returns_structured_error(
    tmp_path, monkeypatch
):
    clear_mysql_env(monkeypatch)
    project = tmp_path / "app"
    write_env(
        project,
        """
        MYSQL_HOST=127.0.0.1
        MYSQL_PORT=3306
        MYSQL_USER=readonly
        MYSQL_PASSWORD=
        """,
    )
    monkeypatch.setenv("MYSQL_PORT", "not-a-port")

    with pytest.raises(ConfigResolutionError) as exc_info:
        load_config(project_path=str(project))

    payload = exc_info.value.to_response()
    assert payload["error"] == "incomplete_mysql_mcp_env"
    assert payload["missing_keys"] == ["MYSQL_PORT"]
