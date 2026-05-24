from pathlib import Path


def test_skill_requires_project_path_for_mcp_tools():
    skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    text = skill.read_text(encoding="utf-8")

    assert "project_path" in text
    assert "current project root" in text
    assert ".mysql.mcp.env" in text
    assert "missing_mysql_mcp_env" in text
    assert ".gitignore" in text
