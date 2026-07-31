from training_sync import config

def test_intervals_key_reads_env_without_exposing_it(monkeypatch):
    monkeypatch.setenv("INTERVALS_API_KEY", "secret")
    assert config.load_intervals_api_key() == "secret"

def test_intervals_key_reads_local_file_and_strips_whitespace(monkeypatch, tmp_path):
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)
    (tmp_path / "intervals-api-key").write_text(" local-secret\n")
    monkeypatch.setattr(config, "intervals_api_key_path", lambda: tmp_path / "intervals-api-key")
    assert config.load_intervals_api_key() == "local-secret"
