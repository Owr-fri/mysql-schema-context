from pathlib import Path
import sys
import types
from typing import Optional, Union, get_args, get_origin

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

    def mysql_describe_table(self, schema, table, columns=None):
        self.calls.append(("mysql_describe_table", schema, table, columns))
        return [{"column_name": "id"}]


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


def test_with_tools_does_not_convert_operation_errors(monkeypatch):
    class FakeConfigError(Exception):
        def to_response(self):
            return {"error": "missing_mysql_mcp_env"}

    monkeypatch.setattr(server, "ConfigResolutionError", FakeConfigError)
    monkeypatch.setattr(server, "_build_tools", lambda project_path=None: FakeTools())

    try:
        server._with_tools(
            "E:/app",
            lambda tools: (_ for _ in ()).throw(FakeConfigError("boom")),
        )
    except FakeConfigError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("Expected operation ConfigResolutionError to propagate")


def test_build_server_tool_annotations_and_project_path_forwarding(monkeypatch):
    class FakeFastMCP:
        def __init__(self, name):
            self.name = name
            self.tools = {}

        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    fake_mcp = types.ModuleType("mcp")
    fake_server = types.ModuleType("mcp.server")
    fake_fastmcp = types.ModuleType("mcp.server.fastmcp")
    fake_fastmcp.FastMCP = FakeFastMCP
    fake_server.fastmcp = fake_fastmcp
    fake_mcp.server = fake_server

    monkeypatch.setitem(sys.modules, "mcp", fake_mcp)
    monkeypatch.setitem(sys.modules, "mcp.server", fake_server)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fake_fastmcp)

    calls = []

    def fake_with_tools(project_path, operation):
        calls.append(project_path)
        return operation(FakeTools())

    monkeypatch.setattr(server, "_with_tools", fake_with_tools)

    mcp = server.build_server()

    assert _allows_optional(mcp.tools["mysql_ping"].__annotations__["project_path"], str)
    assert _allows_optional(mcp.tools["mysql_execute_select"].__annotations__["max_rows"], int)
    assert _allows_optional(mcp.tools["mysql_describe_table"].__annotations__["columns"], list)

    result = mcp.tools["mysql_list_tables"]("shop", project_path="E:/app")

    assert calls == ["E:/app"]
    assert result == [{"table_name": "users"}]


def test_build_server_describe_table_forwards_column_filter(monkeypatch):
    class FakeFastMCP:
        def __init__(self, name):
            self.name = name
            self.tools = {}

        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    fake_mcp = types.ModuleType("mcp")
    fake_server = types.ModuleType("mcp.server")
    fake_fastmcp = types.ModuleType("mcp.server.fastmcp")
    fake_fastmcp.FastMCP = FakeFastMCP
    fake_server.fastmcp = fake_fastmcp
    fake_mcp.server = fake_server

    monkeypatch.setitem(sys.modules, "mcp", fake_mcp)
    monkeypatch.setitem(sys.modules, "mcp.server", fake_server)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fake_fastmcp)

    fake_tools = FakeTools()

    def fake_with_tools(project_path, operation):
        return operation(fake_tools)

    monkeypatch.setattr(server, "_with_tools", fake_with_tools)

    mcp = server.build_server()

    result = mcp.tools["mysql_describe_table"](
        "app",
        "users",
        columns=["id", "email"],
        project_path="E:/app",
    )

    assert result == [{"column_name": "id"}]
    assert fake_tools.calls == [("mysql_describe_table", "app", "users", ["id", "email"])]


def _allows_optional(annotation, expected_type):
    args = get_args(annotation)
    return (
        annotation == Optional[expected_type]
        or get_origin(annotation) is Union
        and type(None) in args
        and any(arg == expected_type or get_origin(arg) is expected_type for arg in args)
    )
