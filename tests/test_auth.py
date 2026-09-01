from hatui.config import GraphConfig, HatuiConfig, LdapConfig, load_config
from hatui.services.auth import graph_token_form, graph_token_url, ldap_bind_identity
from hatui.services.connectors.graph import GraphBackend
from hatui.services.connectors.ldap import LdapDirectoryBackend
from hatui.services.protocol import NotConfiguredError


def test_ldap_login_identity_prefers_username():
    cfg = LdapConfig(enabled=True, auth="login", server="dc.lab", username="admin@blackrainlabs.corp", bind_dn="CN=svc,DC=lab")
    assert ldap_bind_identity(cfg) == "admin@blackrainlabs.corp"


def test_ldap_bind_identity_prefers_dn():
    cfg = LdapConfig(enabled=True, auth="bind", server="dc.lab", username="admin@lab", bind_dn="CN=svc,DC=lab")
    assert ldap_bind_identity(cfg) == "CN=svc,DC=lab"


def test_ldap_login_constructs_without_bind_dn():
    be = LdapDirectoryBackend(
        LdapConfig(enabled=True, auth="login", server="dc.blackrainlabs.corp", username="ops@blackrainlabs.corp")
    )
    assert be.cfg.username == "ops@blackrainlabs.corp"


def test_ldap_still_requires_server_or_identity():
    try:
        LdapDirectoryBackend(LdapConfig(enabled=True, server="dc.lab"))
        raise AssertionError("expected NotConfiguredError")
    except NotConfiguredError:
        pass


def test_graph_login_allows_missing_secret():
    be = GraphBackend(
        GraphConfig(
            enabled=True,
            auth="login",
            tenant_id="blackrainlabs.onmicrosoft.com",
            client_id="public-client",
            username="ops@blackrainlabs.corp",
            password="secret",
        )
    )
    form = graph_token_form(be.cfg)
    assert form["grant_type"] == "password"
    assert form["username"] == "ops@blackrainlabs.corp"
    assert "client_secret" not in form
    assert "oauth2/v2.0/token" in graph_token_url(be.cfg)


def test_graph_login_includes_secret_when_present():
    cfg = GraphConfig(
        enabled=True,
        auth="login",
        tenant_id="t",
        client_id="c",
        client_secret="s",
        username="ops@lab",
        password="p",
    )
    form = graph_token_form(cfg)
    assert form["grant_type"] == "password"
    assert form["client_secret"] == "s"


def test_graph_client_credentials_still_needs_secret():
    try:
        GraphBackend(GraphConfig(enabled=True, auth="client_credentials", tenant_id="t", client_id="c"))
        raise AssertionError("expected NotConfiguredError")
    except NotConfiguredError:
        pass


def test_graph_client_credentials_form():
    form = graph_token_form(
        GraphConfig(enabled=True, auth="client_credentials", tenant_id="t", client_id="c", client_secret="s")
    )
    assert form["grant_type"] == "client_credentials"
    assert "username" not in form


def test_load_config_shared_login(tmp_path, monkeypatch):
    path = tmp_path / "hatui.toml"
    path.write_text('mode = "live"\n[ldap]\nenabled = true\nserver = "dc.lab"\n', encoding="utf-8")
    monkeypatch.setenv("HATUI_USERNAME", "admin@blackrainlabs.corp")
    monkeypatch.setenv("HATUI_PASSWORD", "hunter2")
    cfg = load_config(path)
    assert cfg.ldap.username == "admin@blackrainlabs.corp"
    assert cfg.ldap.password == "hunter2"
    assert cfg.graph.username == "admin@blackrainlabs.corp"
    assert cfg.graph.password == "hunter2"
    assert cfg.session_user == "admin@blackrainlabs.corp"
    assert cfg.needs_login_prompt is False


def test_needs_login_prompt_when_live_and_blank():
    cfg = HatuiConfig(mode="live")
    cfg.ldap.enabled = True
    cfg.ldap.server = "dc.lab"
    cfg.ldap.username = "admin@lab"
    assert cfg.needs_login_prompt is True
