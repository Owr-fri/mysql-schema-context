from pathlib import Path
import re


def _skill_text() -> str:
    skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    return skill.read_text(encoding="utf-8")


def test_skill_requires_project_path_for_mcp_tools():
    text = _skill_text()

    assert "current project root" in text
    required_calls = [
        "mysql_ping(project_path=current_project_root)",
        "mysql_list_schemas(project_path=current_project_root)",
        "mysql_list_tables(schema, project_path=current_project_root)",
        "mysql_execute_select(sql, max_rows, project_path=current_project_root)",
    ]
    for call in required_calls:
        assert call in text


def test_missing_env_guidance_is_local_readonly_and_git_ignored():
    text = _skill_text()

    assert "missing_mysql_mcp_env" in text
    assert "stop database discovery" in text
    assert ".mysql.mcp.env" in text

    template_keys = [
        "MYSQL_HOST=127.0.0.1",
        "MYSQL_PORT=3306",
        "MYSQL_USER=readonly_user",
        "MYSQL_PASSWORD=",
        "MYSQL_DATABASE=",
        "MYSQL_CONNECT_TIMEOUT=5",
        "MYSQL_MAX_ROWS=100",
    ]
    for key in template_keys:
        assert key in text

    assert "Do not fill in real passwords" in text
    assert "read-only database account" in text
    assert ".gitignore" in text

    lowered = text.lower()
    assert re.search(r"create or update[^.]*\.gitignore", lowered)
    assert re.search(r"do not ask[^.]*passwords?[^.]*chat", lowered)
    assert re.search(r"enter credentials[^.]*locally[^.]*\.mysql\.mcp\.env", lowered)
