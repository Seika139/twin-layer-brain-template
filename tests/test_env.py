from __future__ import annotations

from compiler import env


def test_load_dotenv_prefers_repo_env_over_parent_env(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(env, "BASE_DIR", tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-parent")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-repo\n", encoding="utf-8")

    env.load_dotenv()

    assert env.os.environ["OPENAI_API_KEY"] == "sk-repo"


def test_load_dotenv_keeps_parent_env_when_repo_env_is_absent(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(env, "BASE_DIR", tmp_path)
    monkeypatch.setenv("BRAIN_PORT", "15201")

    env.load_dotenv()

    assert env.os.environ["BRAIN_PORT"] == "15201"
