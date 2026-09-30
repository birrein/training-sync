from pathlib import Path

import pytest
import requests

from training_sync.garmin import auth


class FakeGarmin:
    login_calls = []

    def __init__(self, email=None, password=None):
        self.email = email
        self.password = password

    def login(self, tokenstore):
        self.login_calls.append(tokenstore)


def test_get_client_uses_training_sync_config_token_path(monkeypatch, tmp_path):
    token_path = tmp_path / "training-sync" / "garmin-token.json"
    token_path.parent.mkdir()
    token_path.write_text("{}", encoding="utf-8")
    FakeGarmin.login_calls = []

    monkeypatch.setattr(auth, "Garmin", FakeGarmin)
    monkeypatch.setattr(auth, "garmin_token_path", lambda: token_path)

    auth.get_client()

    assert FakeGarmin.login_calls == [str(token_path)]


def test_get_client_does_not_report_network_failure_as_expired_token(monkeypatch, tmp_path):
    token_path = tmp_path / "training-sync" / "garmin-token.json"
    token_path.parent.mkdir()
    token_path.write_text("{}", encoding="utf-8")

    class OfflineGarmin:
        def login(self, tokenstore):
            try:
                raise requests.ConnectionError("offline")
            except requests.ConnectionError as exc:
                raise RuntimeError("profile lookup failed") from exc

    monkeypatch.setattr(auth, "Garmin", OfflineGarmin)
    monkeypatch.setattr(auth, "garmin_token_path", lambda: token_path)
    monkeypatch.setattr(auth.sys.stdin, "isatty", lambda: pytest.fail("must not prompt for login"))

    with pytest.raises(SystemExit, match="network connection"):
        auth.get_client()
