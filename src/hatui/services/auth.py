from __future__ import annotations

from hatui.config import GraphConfig, LdapConfig
from hatui.services.protocol import NotConfiguredError


def ldap_bind_identity(cfg: LdapConfig) -> str:
    """Operator identity used for the LDAP bind (login UPN or service DN)."""
    if cfg.auth == "bind":
        identity = cfg.bind_dn or cfg.username
    else:
        identity = cfg.username or cfg.bind_dn
    if not identity:
        raise NotConfiguredError(
            "LDAP login requires a username (UPN or DOMAIN\\sAM) or bind_dn."
        )
    return identity


def graph_token_form(cfg: GraphConfig) -> dict[str, str]:
    """Form body for the Azure AD token endpoint."""
    if cfg.auth == "login":
        if not cfg.username:
            raise NotConfiguredError("Graph login requires a username (UPN).")
        if not cfg.password:
            raise NotConfiguredError("Graph login requires a password.")
        form = {
            "grant_type": "password",
            "client_id": cfg.client_id,
            "username": cfg.username,
            "password": cfg.password,
            "scope": cfg.scope,
        }
        if cfg.client_secret:
            form["client_secret"] = cfg.client_secret
        return form
    if not cfg.client_secret:
        raise NotConfiguredError("HATUI_GRAPH_CLIENT_SECRET is not set.")
    return {
        "grant_type": "client_credentials",
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "scope": cfg.scope,
    }


def graph_token_url(cfg: GraphConfig) -> str:
    tenant = cfg.tenant_id or "organizations"
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
