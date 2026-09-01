from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["mock", "live"]
LdapAuth = Literal["login", "bind"]
GraphAuth = Literal["login", "client_credentials"]


class LdapConfig(BaseModel):
    enabled: bool = False
    auth: LdapAuth = "login"
    server: str = ""
    username: str = ""
    bind_dn: str = ""
    base_dn: str = ""
    use_ssl: bool = True
    password: str = ""


class GraphConfig(BaseModel):
    enabled: bool = False
    auth: GraphAuth = "login"
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    scope: str = "https://graph.microsoft.com/.default"


class HatuiConfig(BaseModel):
    mode: Mode = "mock"
    org_name: str = "BlackRainLabs"
    domain: str = "blackrainlabs.corp"
    entra_tenant: str = "blackrainlabs.onmicrosoft.com"
    exchange_org: str = "BlackRainLabs"
    session_user: str = ""
    ldap: LdapConfig = Field(default_factory=LdapConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)

    @property
    def ldap_live(self) -> bool:
        identity = self.ldap.username or self.ldap.bind_dn
        return self.mode == "live" and self.ldap.enabled and bool(self.ldap.server and identity)

    @property
    def graph_live(self) -> bool:
        if not (self.mode == "live" and self.graph.enabled and self.graph.tenant_id and self.graph.client_id):
            return False
        if self.graph.auth == "login":
            return bool(self.graph.username)
        return True

    @property
    def needs_login_prompt(self) -> bool:
        if self.mode != "live":
            return False
        ldap_ready = (not self.ldap.enabled) or bool(self.ldap.password)
        if self.graph.auth == "login":
            graph_ready = (not self.graph.enabled) or bool(self.graph.password)
        else:
            graph_ready = (not self.graph.enabled) or bool(self.graph.client_secret)
        return not (ldap_ready and graph_ready)


def _load_toml(path: Path) -> dict:
    import tomllib

    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_config(path: str | Path | None = None) -> HatuiConfig:
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    env_path = os.environ.get("HATUI_CONFIG")
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(
        [
            Path.cwd() / "hatui.toml",
            Path.home() / ".config" / "hatui" / "hatui.toml",
        ]
    )

    data: dict = {}
    for candidate in candidates:
        if candidate.is_file():
            data = _load_toml(candidate)
            break

    cfg = HatuiConfig.model_validate(data)
    shared_user = os.environ.get("HATUI_USERNAME", "")
    shared_password = os.environ.get("HATUI_PASSWORD", "")
    ldap_user = os.environ.get("HATUI_LDAP_USERNAME", "") or shared_user
    ldap_pw = os.environ.get("HATUI_LDAP_PASSWORD", "") or shared_password
    graph_user = os.environ.get("HATUI_GRAPH_USERNAME", "") or shared_user
    graph_pw = os.environ.get("HATUI_GRAPH_PASSWORD", "") or shared_password
    graph_secret = os.environ.get("HATUI_GRAPH_CLIENT_SECRET", "")
    if ldap_user:
        cfg.ldap.username = ldap_user
    if ldap_pw:
        cfg.ldap.password = ldap_pw
    if graph_user:
        cfg.graph.username = graph_user
    if graph_pw:
        cfg.graph.password = graph_pw
    if graph_secret:
        cfg.graph.client_secret = graph_secret
    cfg.session_user = cfg.session_user or cfg.ldap.username or cfg.graph.username
    return cfg
