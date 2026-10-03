from sentinel.config import Settings

VARIABEL = ("DATABASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "DEMO_MODE", "PARAMETER_PATH")


def test_nilai_default_tanpa_environment(monkeypatch):
    for nama in VARIABEL:
        monkeypatch.delenv(nama, raising=False)

    s = Settings(_env_file=None)

    assert s.anthropic_model == "claude-sonnet-5"
    assert s.anthropic_api_key is None
    assert s.demo_mode is False
    assert s.parameter_path.parts[-2:] == ("config", "parameter.yaml")


def test_environment_mengganti_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "model-lain")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")

    s = Settings(_env_file=None)

    assert s.anthropic_model == "model-lain"
    assert s.demo_mode is True
    assert s.database_url == "postgresql+psycopg://u:p@h:5432/d"
