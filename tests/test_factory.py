from pathlib import Path

from hatui.config import load_config
from hatui.services.factory import create_backend
from hatui.services.mock.backend import MockBackend
from hatui.ui.catalog import CATALOG, resolve_jump


def test_load_config_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HATUI_CONFIG", raising=False)
    cfg = load_config()
    assert cfg.mode == "mock"
    assert cfg.org_name == "BlackRainLabs"


def test_load_config_file(tmp_path):
    path = tmp_path / "hatui.toml"
    path.write_text(
        'mode = "mock"\norg_name = "Test Org"\ndomain = "test.lab"\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.org_name == "Test Org"
    assert cfg.domain == "test.lab"


def test_factory_mock():
    cfg = load_config(Path(__file__).resolve().parents[1] / "hatui.toml")
    backend = create_backend(cfg)
    assert isinstance(backend, MockBackend)
    lights = backend.connector_status()
    assert lights
    assert all(c.live is False for c in lights)


def test_catalog_covers_admin_surface():
    required = {
        "users",
        "groups",
        "computers",
        "mailboxes",
        "permissions",
        "ous",
        "dcs",
        "gpos",
        "cloud_users",
        "licenses",
        "locks",
        "privileged",
        "jobs",
    }
    assert required <= set(CATALOG)
    assert resolve_jump("mbx") == "mailboxes"
    assert resolve_jump("sync") == "aadconnect"
    assert resolve_jump("users") == "users"
