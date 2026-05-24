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
