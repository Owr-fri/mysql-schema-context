"""MCP transport wrapper for the MySQL read-only tools."""

from typing import Callable, Optional

from .config import ConfigResolutionError, load_config
from .db import MySQLDatabase
from .tools import MySQLTools


def _build_tools(project_path: Optional[str] = None):
    config = load_config(project_path=project_path)
    return MySQLTools(MySQLDatabase(config), configured_max_rows=config.max_rows)


def _with_tools(project_path: Optional[str], operation: Callable):
    try:
        tools = _build_tools(project_path=project_path)
    except ConfigResolutionError as exc:
        return exc.to_response()
    return operation(tools)


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("mcp is required. Install with: python -m pip install mcp") from exc

    mcp = FastMCP("mysql-readonly")

    @mcp.tool()
    def mysql_ping(project_path: Optional[str] = None):
        """Verify the MySQL connection without returning secrets."""
        return _with_tools(project_path, lambda tools: tools.mysql_ping())

    @mcp.tool()
    def mysql_list_schemas(
        include_system: bool = False,
        project_path: Optional[str] = None,
    ):
        """List MySQL schemas."""
        return _with_tools(
            project_path,
            lambda tools: tools.mysql_list_schemas(include_system=include_system),
        )

    @mcp.tool()
    def mysql_list_tables(schema: str, project_path: Optional[str] = None):
        """List tables for a schema."""
        return _with_tools(project_path, lambda tools: tools.mysql_list_tables(schema))

    @mcp.tool()
    def mysql_describe_table(
        schema: str,
        table: str,
        project_path: Optional[str] = None,
    ):
        """Describe columns for a schema table."""
        return _with_tools(
            project_path,
            lambda tools: tools.mysql_describe_table(schema, table),
        )

    @mcp.tool()
    def mysql_show_create_table(
        schema: str,
        table: str,
        project_path: Optional[str] = None,
    ):
        """Return SHOW CREATE TABLE output for one table."""
        return _with_tools(
            project_path,
            lambda tools: tools.mysql_show_create_table(schema, table),
        )

    @mcp.tool()
    def mysql_list_relationships(schema: str, project_path: Optional[str] = None):
        """List keys, indexes, foreign keys, and inferred relationship hints."""
        return _with_tools(
            project_path,
            lambda tools: tools.mysql_list_relationships(schema),
        )

    @mcp.tool()
    def mysql_execute_select(
        sql: str,
        max_rows: Optional[int] = None,
        project_path: Optional[str] = None,
    ):
        """Run one read-only SELECT or WITH ... SELECT statement with a row cap."""
        return _with_tools(
            project_path,
            lambda tools: tools.mysql_execute_select(sql, max_rows=max_rows),
        )

    return mcp


def main():
    build_server().run()


if __name__ == "__main__":
    main()
