"""MCP transport wrapper for the MySQL read-only tools."""

from .config import load_config
from .db import MySQLDatabase
from .tools import MySQLTools


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("mcp is required. Install with: python -m pip install mcp") from exc

    config = load_config()
    tools = MySQLTools(MySQLDatabase(config), configured_max_rows=config.max_rows)
    mcp = FastMCP("mysql-readonly")

    @mcp.tool()
    def mysql_ping():
        """Verify the MySQL connection without returning secrets."""
        return tools.mysql_ping()

    @mcp.tool()
    def mysql_list_schemas(include_system: bool = False):
        """List MySQL schemas."""
        return tools.mysql_list_schemas(include_system=include_system)

    @mcp.tool()
    def mysql_list_tables(schema: str):
        """List tables for a schema."""
        return tools.mysql_list_tables(schema)

    @mcp.tool()
    def mysql_describe_table(schema: str, table: str):
        """Describe columns for a schema table."""
        return tools.mysql_describe_table(schema, table)

    @mcp.tool()
    def mysql_show_create_table(schema: str, table: str):
        """Return SHOW CREATE TABLE output for one table."""
        return tools.mysql_show_create_table(schema, table)

    @mcp.tool()
    def mysql_list_relationships(schema: str):
        """List keys, indexes, foreign keys, and inferred relationship hints."""
        return tools.mysql_list_relationships(schema)

    @mcp.tool()
    def mysql_execute_select(sql: str, max_rows: int = None):
        """Run one read-only SELECT or WITH ... SELECT statement with a row cap."""
        return tools.mysql_execute_select(sql, max_rows=max_rows)

    return mcp


def main():
    build_server().run()


if __name__ == "__main__":
    main()
