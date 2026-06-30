from pathlib import Path

from garmin_sync import auth


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
