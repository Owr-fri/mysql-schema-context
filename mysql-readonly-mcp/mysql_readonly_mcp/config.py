"""Environment-based configuration for the MySQL read-only MCP server."""

import os
from dataclasses import dataclass
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


@dataclass(frozen=True)
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    connect_timeout: int
    max_rows: int

    def safe_summary(self):
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "database": self.database,
            "connect_timeout": self.connect_timeout,
            "max_rows": self.max_rows,
        }


def load_config(project_path: str = None) -> MySQLConfig:
    values = {}
    if project_path is not None:
        resolved_project_path = _resolve_project_path(project_path)
        env_file = resolved_project_path / ENV_FILE_NAME
        if not env_file.is_file():
            raise ConfigResolutionError(
                {
                    "error": "missing_mysql_mcp_env",
                    "project_path": str(resolved_project_path),
                    "expected_file": str(env_file),
                    "required_keys": list(REQUIRED_ENV_KEYS),
                    "template": ENV_TEMPLATE,
                }
            )

        values = _parse_env_file(env_file)
        missing_keys = _invalid_required_project_keys(values)
        if missing_keys:
            raise ConfigResolutionError(
                {
                    "error": "incomplete_mysql_mcp_env",
                    "project_path": str(resolved_project_path),
                    "expected_file": str(env_file),
                    "missing_keys": missing_keys,
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


def _resolve_project_path(project_path: str) -> Path:
    path = Path(project_path).expanduser().resolve()
    if not path.is_dir():
        raise ConfigResolutionError(
            {"error": "invalid_project_path", "project_path": str(path)}
        )
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


def _invalid_required_project_keys(values: dict) -> list:
    invalid_keys = []
    for key in REQUIRED_ENV_KEYS:
        value = _effective_project_value(values, key)
        if key == "MYSQL_PASSWORD":
            if value is None:
                invalid_keys.append(key)
            continue

        if value is None or value.strip() == "":
            invalid_keys.append(key)
            continue

        if key == "MYSQL_PORT":
            try:
                int(value.strip())
            except ValueError:
                invalid_keys.append(key)

    return invalid_keys


def _effective_project_value(values: dict, name: str):
    return os.environ[name] if name in os.environ else values.get(name)


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
