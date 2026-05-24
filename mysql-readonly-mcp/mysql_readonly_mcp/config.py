"""Environment-based configuration for the MySQL read-only MCP server."""

import os
from dataclasses import dataclass


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


def load_config() -> MySQLConfig:
    return MySQLConfig(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=_int_env("MYSQL_PORT", 3306),
        user=os.environ.get("MYSQL_USER", ""),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", ""),
        connect_timeout=_int_env("MYSQL_CONNECT_TIMEOUT", 5),
        max_rows=max(1, _int_env("MYSQL_MAX_ROWS", 100)),
    )


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default
