import pytest

from training_sync import config


def test_vault_root_uses_training_sync_environment_override(monkeypatch, tmp_path):
    configured_root = tmp_path / "shared-vault"
    local_root = tmp_path / "local-vault"
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    config.vault_root_path().write_text(str(local_root), encoding="utf-8")
    monkeypatch.setenv("TRAINING_SYNC_VAULT_ROOT", str(configured_root))

    assert config.vault_root() == configured_root


def test_vault_root_uses_local_file_when_environment_override_is_absent(monkeypatch, tmp_path):
    monkeypatch.delenv("TRAINING_SYNC_VAULT_ROOT", raising=False)
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    local_root = tmp_path / "local-vault"
    config.vault_root_path().write_text(f"  {local_root}  \n", encoding="utf-8")

    assert config.vault_root() == local_root


@pytest.mark.parametrize("configured_root", [None, "", "   "])
def test_vault_root_requires_configuration_when_both_sources_are_absent(
    monkeypatch,
    tmp_path,
    configured_root,
):
    monkeypatch.delenv("TRAINING_SYNC_VAULT_ROOT", raising=False)
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    if configured_root is not None:
        monkeypatch.setenv("TRAINING_SYNC_VAULT_ROOT", configured_root)

    with pytest.raises(ValueError, match="vault-root"):
        config.vault_root()


@pytest.mark.parametrize("configured_root", ["relative-vault", "../relative-vault"])
def test_vault_root_rejects_relative_configuration(monkeypatch, configured_root):
    monkeypatch.setenv("TRAINING_SYNC_VAULT_ROOT", configured_root)

    with pytest.raises(ValueError, match="absolute"):
        config.vault_root()
