from hatui.config import GraphConfig, LdapConfig
from hatui.services.connectors.graph import GraphBackend
from hatui.services.connectors.ldap import LdapDirectoryBackend
from hatui.services.protocol import NotConfiguredError
from hatui.ui.actions import dispatch
from hatui.services.mock.backend import MockBackend


def test_ldap_not_configured():
    try:
        LdapDirectoryBackend(LdapConfig())
        raise AssertionError("expected NotConfiguredError")
    except NotConfiguredError:
        pass


def test_graph_not_configured():
    try:
        GraphBackend(GraphConfig())
        raise AssertionError("expected NotConfiguredError")
    except NotConfiguredError:
        pass


def test_dispatch_user_mailbox_permission():
    be = MockBackend()
    dispatch(
        be,
        "users",
        "new",
        None,
        {"given_name": "Kit", "surname": "Rook", "department": "Security", "origin": "on-prem"},
    )
    user = next(u for u in be.list_users() if u.surname == "Rook")
    dispatch(be, "users", "enable_mailbox", user, {"mailbox_type": "RemoteMailbox"})
    user = be.get_user(user.id)
    mb = be.get_mailbox(user.mailbox_id)
    elena = next(u for u in be.list_users() if u.display_name == "Elena Voss")
    dispatch(
        be,
        "mailboxes",
        "grant",
        mb,
        {"trustee": elena.upn, "rights": "FullAccess", "automapping": "Y"},
    )
    perms = be.list_permissions(mb.id)
    assert any(p.trustee == elena.upn and p.rights.value == "FullAccess" for p in perms)
