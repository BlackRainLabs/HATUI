from __future__ import annotations

from hatui.config import HatuiConfig
from hatui.models import ConnectorStatus, ForestHealth, HealthState
from hatui.services.mock.backend import MockBackend
from hatui.services.protocol import HatuiBackend, NotConfiguredError

DIR_METHODS = {
    "list_users",
    "get_user",
    "create_user",
    "set_user_enabled",
    "unlock_user",
    "reset_password",
    "move_user",
    "list_groups",
    "create_group",
    "set_group_members",
    "add_group_member",
    "remove_group_member",
    "list_computers",
    "set_computer_enabled",
    "list_contacts",
    "list_service_accounts",
    "list_ous",
    "create_ou",
    "list_dcs",
    "list_fsmo",
    "list_sites",
    "list_gpos",
    "set_gpo_enabled",
    "list_replication",
    "list_trusts",
}

MAIL_METHODS = {
    "list_mailboxes",
    "get_mailbox",
    "create_mailbox",
    "enable_mailbox",
    "set_mailbox_forwarding",
    "set_litigation_hold",
    "set_auto_reply",
    "set_archive",
    "set_hidden",
    "list_permissions",
    "grant_permission",
    "revoke_permission",
    "list_mail_flow",
}

CLOUD_METHODS = {
    "list_cloud_users",
    "list_guests",
    "list_licenses",
    "assign_license",
    "remove_license",
    "list_roles",
    "list_soft_deleted",
    "restore_deleted",
}


class CompositeBackend:
    def __init__(
        self,
        mock: MockBackend,
        *,
        directory: object | None = None,
        mail: object | None = None,
        cloud: object | None = None,
        ldap_live: bool = False,
        graph_live: bool = False,
        config: HatuiConfig | None = None,
    ) -> None:
        self._mock = mock
        self._directory = directory or mock
        self._mail = mail or mock
        self._cloud = cloud or mock
        self.ldap_live = ldap_live
        self.graph_live = graph_live
        self.config = config

    def __getattr__(self, name: str):
        if name in DIR_METHODS:
            return getattr(self._directory, name)
        if name in MAIL_METHODS:
            return getattr(self._mail, name)
        if name in CLOUD_METHODS:
            return getattr(self._cloud, name)
        return getattr(self._mock, name)

    def forest_health(self) -> ForestHealth:
        health = self._mock.forest_health()
        if self.ldap_live or self.graph_live:
            health.mode = "LIVE"
            health.forest_state = HealthState.HEALTHY if self.ldap_live else health.forest_state
            health.exo_state = HealthState.ONLINE if self.graph_live else health.exo_state
            health.entra_state = HealthState.SYNCED if self.graph_live else health.entra_state
        else:
            health.mode = "MOCK"
        return health

    def connector_status(self) -> list[ConnectorStatus]:
        ldap_detail = "mock forest"
        graph_detail = self.config.entra_tenant if self.config else ""
        if self.config and self.ldap_live:
            who = self.config.ldap.username or self.config.ldap.bind_dn
            ldap_detail = f"{self.config.ldap.auth} {who} @ {self.config.ldap.server}"
        if self.config and self.graph_live:
            if self.config.graph.auth == "login":
                graph_detail = f"login {self.config.graph.username}"
            else:
                graph_detail = f"client_credentials {self.config.entra_tenant}"
        return [
            ConnectorStatus(
                name="Directory",
                kind="LDAP",
                live=self.ldap_live,
                detail=ldap_detail,
                health="LIVE" if self.ldap_live else "MOCK",
            ),
            ConnectorStatus(
                name="Entra / Graph",
                kind="Graph",
                live=self.graph_live,
                detail=graph_detail,
                health="LIVE" if self.graph_live else "MOCK",
            ),
            ConnectorStatus(
                name="Exchange",
                kind="Graph",
                live=self.graph_live,
                detail=self.config.exchange_org if self.config else "",
                health="LIVE" if self.graph_live else "MOCK",
            ),
            ConnectorStatus(
                name="AAD Connect",
                kind="Hybrid",
                live=False,
                detail="status via mock/hybrid inventory",
                health="MOCK",
            ),
        ]

    def authenticate(self) -> None:
        for target in (self._directory, self._mail, self._cloud):
            if target is self._mock:
                continue
            method = getattr(target, "authenticate", None)
            if callable(method):
                method()


def create_backend(config: HatuiConfig) -> HatuiBackend:
    mock = MockBackend()
    if config.mode != "live":
        mock.store.connectors = CompositeBackend(mock, config=config).connector_status()
        return mock

    ldap_be = None
    graph_be = None
    ldap_live = False
    graph_live = False
    if config.ldap_live:
        from hatui.services.connectors.ldap import LdapDirectoryBackend

        try:
            ldap_be = LdapDirectoryBackend(config.ldap)
            ldap_live = True
        except NotConfiguredError:
            ldap_be = None
    if config.graph_live:
        from hatui.services.connectors.graph import GraphBackend

        try:
            graph_be = GraphBackend(config.graph)
            graph_live = True
        except NotConfiguredError:
            graph_be = None

    composite = CompositeBackend(
        mock,
        directory=ldap_be,
        mail=graph_be,
        cloud=graph_be,
        ldap_live=ldap_live,
        graph_live=graph_live,
        config=config,
    )
    mock.store.connectors = composite.connector_status()
    health = composite.forest_health()
    mock.store.connectors = composite.connector_status()
    _ = health
    return composite  # type: ignore[return-value]
