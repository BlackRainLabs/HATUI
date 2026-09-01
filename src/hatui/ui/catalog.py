from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from types import SimpleNamespace

from hatui.models import Group, GroupType, Mailbox, MailboxType, User
from hatui.ui.modals import FieldSpec

Loader = Callable[[Any, str], list[Any]]
RowFn = Callable[[Any], list[str]]
InspectFn = Callable[[Any, Any], list[tuple[str, str]]]
KeyFn = Callable[[Any], str]


def _dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")


def _yn(value: bool) -> str:
    return "Y" if value else "n"


def _ou_name(backend: Any, ou_id: str) -> str:
    for ou in backend.list_ous():
        if ou.id == ou_id:
            return ou.name
    return ou_id or "—"


NAV: list[tuple[str, list[tuple[str, str]]]] = [
    ("DASHBOARD", []),
    (
        "IDENTITY",
        [
            ("users", "Users"),
            ("groups", "Groups"),
            ("computers", "Computers"),
            ("contacts", "Contacts"),
            ("service_accounts", "Service Accounts"),
        ],
    ),
    (
        "DIRECTORY",
        [
            ("ous", "OUs"),
            ("dcs", "Domain Controllers"),
            ("fsmo", "FSMO"),
            ("sites", "Sites"),
            ("gpos", "GPOs"),
            ("replication", "Replication"),
            ("trusts", "Trusts"),
        ],
    ),
    (
        "EXCHANGE",
        [
            ("mailboxes", "Mailboxes"),
            ("permissions", "Permissions"),
            ("recipients", "Recipients"),
            ("distribution", "Distribution"),
            ("resources", "Shared / Resources"),
            ("mailflow", "Mail Flow"),
        ],
    ),
    (
        "ENTRA / HYBRID",
        [
            ("cloud_users", "Cloud Users"),
            ("guests", "Guests"),
            ("licenses", "Licenses"),
            ("roles", "Directory Roles"),
            ("aadconnect", "AAD Connect"),
            ("softdeleted", "Soft-Deleted"),
        ],
    ),
    (
        "SECURITY",
        [
            ("locks", "Locks / Passwords"),
            ("privileged", "Privileged Access"),
        ],
    ),
    (
        "OPS",
        [
            ("jobs", "Jobs"),
            ("audit", "Audit Log"),
            ("connectors", "Connectors"),
            ("settings", "Settings"),
        ],
    ),
]


@dataclass
class Column:
    label: str


@dataclass
class ActionSpec:
    id: str
    label: str
    needs_selection: bool = True
    destructive: bool = False
    confirm: str | None = None
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass
class ModuleSpec:
    id: str
    title: str
    columns: list[Column]
    loader: Loader
    row: RowFn
    inspect: InspectFn
    key: KeyFn
    actions: list[ActionSpec] = field(default_factory=list)


def _user_row(user: User) -> list[str]:
    return [
        user.display_name,
        user.sam,
        user.origin.value,
        _yn(user.enabled),
        "LOCK" if user.locked else "",
        "MBX" if user.mailbox_id else "",
        user.department,
    ]


def _user_inspect(user: User, backend: Any) -> list[tuple[str, str]]:
    groups = []
    for gid in user.group_ids:
        g = next((x for x in backend.list_groups() if x.id == gid), None)
        groups.append(g.name if g else gid)
    return [
        ("Display name", user.display_name),
        ("UPN", user.upn),
        ("SAM", user.sam),
        ("Mail", user.mail or "—"),
        ("Origin", user.origin.value),
        ("OU", _ou_name(backend, user.ou)),
        ("Enabled", _yn(user.enabled)),
        ("Locked", _yn(user.locked)),
        ("Must change pwd", _yn(user.must_change_password)),
        ("Department", user.department),
        ("Title", user.title),
        ("Office", user.office),
        ("ImmutableId", user.immutable_id or "—"),
        ("Last sync", _dt(user.last_sync)),
        ("Last logon", _dt(user.last_logon)),
        ("Licenses", ", ".join(user.licenses) or "—"),
        ("Mailbox", user.mailbox_id or "—"),
        ("Groups", ", ".join(groups) or "—"),
        ("Sync error", user.sync_error or "—"),
        ("Guest", _yn(user.guest)),
    ]


def _mb_row(mb: Mailbox) -> list[str]:
    return [
        mb.display_name,
        mb.alias,
        mb.mailbox_type.value,
        mb.primary_smtp,
        _yn(mb.licensed),
        f"{mb.used_gb:.0f}/{mb.quota_gb:.0f}G",
        "HOLD" if mb.litigation_hold else "",
    ]


def _mb_inspect(mb: Mailbox, backend: Any) -> list[tuple[str, str]]:
    perms = backend.list_permissions(mb.id)
    return [
        ("Display name", mb.display_name),
        ("Alias", mb.alias),
        ("SMTP", mb.primary_smtp),
        ("Type", mb.mailbox_type.value),
        ("Recipient", mb.recipient_type),
        ("Database", mb.database),
        ("Licensed", _yn(mb.licensed)),
        ("Quota", f"{mb.used_gb} / {mb.quota_gb} GB"),
        ("Forwarding", mb.forwarding or "—"),
        ("Litigation hold", _yn(mb.litigation_hold)),
        ("Archive", _yn(mb.archive)),
        ("Auto-reply", _yn(mb.auto_reply)),
        ("Hidden", _yn(mb.hidden)),
        ("Created", _dt(mb.created)),
        ("Permissions", str(len(perms))),
    ]


ORIGIN_OPTS = [
    ("synced (hybrid)", "synced"),
    ("on-prem", "on-prem"),
    ("cloud-only", "cloud-only"),
]
MB_TYPE_OPTS = [
    ("Remote mailbox (hybrid)", "RemoteMailbox"),
    ("User mailbox", "UserMailbox"),
    ("Shared", "SharedMailbox"),
    ("Room", "RoomMailbox"),
    ("Equipment", "EquipmentMailbox"),
]
RIGHT_OPTS = [
    ("Full Access", "FullAccess"),
    ("Send As", "SendAs"),
    ("Send on Behalf", "SendOnBehalf"),
    ("Calendar", "Calendar"),
]
GROUP_TYPE_OPTS = [
    ("Security", "security"),
    ("Distribution", "distribution"),
    ("Mail-enabled security", "mail-enabled-security"),
    ("Microsoft 365", "m365"),
]


def _user_actions() -> list[ActionSpec]:
    return [
        ActionSpec(
            "new",
            "Create user",
            needs_selection=False,
            fields=[
                FieldSpec("given_name", "Given name"),
                FieldSpec("surname", "Surname"),
                FieldSpec("department", "Department", default="Operations"),
                FieldSpec("title", "Title", default="Operator"),
                FieldSpec("origin", "Origin", kind="select", options=ORIGIN_OPTS, default="synced"),
            ],
        ),
        ActionSpec("enable", "Enable account"),
        ActionSpec("disable", "Disable account", destructive=True, confirm="Disable this account?"),
        ActionSpec("unlock", "Unlock account"),
        ActionSpec(
            "reset_password",
            "Reset password",
            destructive=True,
            confirm="Issue a temporary password and force change at next logon?",
        ),
        ActionSpec(
            "enable_mailbox",
            "Enable mailbox",
            fields=[FieldSpec("mailbox_type", "Mailbox type", kind="select", options=MB_TYPE_OPTS, default="RemoteMailbox")],
        ),
        ActionSpec(
            "assign_license",
            "Assign license",
            fields=[FieldSpec("sku", "SKU (E3 / E5 / EXO / P2 or part number)", default="E3")],
        ),
        ActionSpec(
            "move_user",
            "Move to OU",
            fields=[FieldSpec("ou_id", "OU id (ou-sec, ou-eng, …)", default="ou-users")],
        ),
        ActionSpec(
            "add_to_group",
            "Add to group",
            fields=[FieldSpec("group_id", "Group id (g-help, g-da, …)", default="g-help")],
        ),
    ]


def _mailbox_actions() -> list[ActionSpec]:
    return [
        ActionSpec(
            "new",
            "Create mailbox",
            needs_selection=False,
            fields=[
                FieldSpec("display_name", "Display name"),
                FieldSpec("alias", "Alias"),
                FieldSpec("mailbox_type", "Type", kind="select", options=MB_TYPE_OPTS, default="SharedMailbox"),
            ],
        ),
        ActionSpec(
            "forward",
            "Set forwarding",
            fields=[FieldSpec("smtp", "Forward SMTP (blank to clear)", placeholder="user@blackrainlabs.corp")],
        ),
        ActionSpec("hold_on", "Enable litigation hold", destructive=True, confirm="Place mailbox on litigation hold?"),
        ActionSpec("hold_off", "Disable litigation hold"),
        ActionSpec("archive_on", "Enable archive"),
        ActionSpec("archive_off", "Disable archive"),
        ActionSpec("autoreply_on", "Enable auto-reply"),
        ActionSpec("autoreply_off", "Disable auto-reply"),
        ActionSpec("hide", "Hide from GAL"),
        ActionSpec("unhide", "Show in GAL"),
        ActionSpec(
            "grant",
            "Grant permission",
            fields=[
                FieldSpec("trustee", "Trustee UPN / SAM"),
                FieldSpec("rights", "Rights", kind="select", options=RIGHT_OPTS, default="FullAccess"),
                FieldSpec("automapping", "Automapping (Y/n)", default="Y"),
                FieldSpec("calendar_level", "Calendar level", default="Editor"),
            ],
        ),
    ]


CATALOG: dict[str, ModuleSpec] = {}


def _register(spec: ModuleSpec) -> None:
    CATALOG[spec.id] = spec


_register(
    ModuleSpec(
        id="users",
        title="Users",
        columns=[Column(c) for c in ("Name", "SAM", "Origin", "En", "Lock", "Mbx", "Dept")],
        loader=lambda b, q: b.list_users(q),
        row=_user_row,
        inspect=_user_inspect,
        key=lambda u: u.id,
        actions=_user_actions(),
    )
)
_register(
    ModuleSpec(
        id="groups",
        title="Groups",
        columns=[Column(c) for c in ("Name", "Type", "Scope", "Mail", "Members", "Priv")],
        loader=lambda b, q: b.list_groups(q),
        row=lambda g: [g.name, g.group_type.value, g.scope, g.mail or "—", str(len(g.member_ids)), _yn(g.privileged)],
        inspect=lambda g, b: [
            ("Name", g.name),
            ("SAM", g.sam),
            ("Type", g.group_type.value),
            ("Scope", g.scope),
            ("Mail", g.mail or "—"),
            ("OU", _ou_name(b, g.ou)),
            ("Origin", g.origin.value),
            ("Privileged", _yn(g.privileged)),
            ("Members", str(len(g.member_ids))),
            ("Description", g.description or "—"),
        ],
        key=lambda g: g.id,
        actions=[
            ActionSpec(
                "new",
                "Create group",
                needs_selection=False,
                fields=[
                    FieldSpec("name", "Name"),
                    FieldSpec("sam", "SAM"),
                    FieldSpec("group_type", "Type", kind="select", options=GROUP_TYPE_OPTS, default="security"),
                    FieldSpec("mail", "Mail (optional)"),
                ],
            ),
            ActionSpec(
                "add_member",
                "Add member",
                fields=[FieldSpec("member_id", "User id or UPN")],
            ),
            ActionSpec(
                "remove_member",
                "Remove member",
                destructive=True,
                fields=[FieldSpec("member_id", "User id or UPN")],
            ),
        ],
    )
)
_register(
    ModuleSpec(
        id="computers",
        title="Computers",
        columns=[Column(c) for c in ("Name", "OS", "IP", "En", "Managed", "Logon")],
        loader=lambda b, q: b.list_computers(q),
        row=lambda c: [c.name, c.os, c.ip, _yn(c.enabled), _yn(c.managed), _dt(c.last_logon)],
        inspect=lambda c, b: [
            ("Name", c.name),
            ("SAM", c.sam),
            ("OS", c.os),
            ("IP", c.ip or "—"),
            ("OU", _ou_name(b, c.ou)),
            ("Enabled", _yn(c.enabled)),
            ("Managed", _yn(c.managed)),
            ("Last logon", _dt(c.last_logon)),
            ("SPN", ", ".join(c.spn) or "—"),
        ],
        key=lambda c: c.id,
        actions=[
            ActionSpec("enable", "Enable"),
            ActionSpec("disable", "Disable", destructive=True, confirm="Disable this computer account?"),
        ],
    )
)
_register(
    ModuleSpec(
        id="contacts",
        title="Contacts",
        columns=[Column(c) for c in ("Name", "Mail", "Company", "Origin")],
        loader=lambda b, q: b.list_contacts(q),
        row=lambda c: [c.display_name, c.mail, c.company, c.origin.value],
        inspect=lambda c, b: [("Name", c.display_name), ("Mail", c.mail), ("Company", c.company), ("OU", _ou_name(b, c.ou))],
        key=lambda c: c.id,
    )
)
_register(
    ModuleSpec(
        id="service_accounts",
        title="Service Accounts",
        columns=[Column(c) for c in ("SAM", "Name", "Kind", "En", "SPN")],
        loader=lambda b, q: b.list_service_accounts(q),
        row=lambda a: [a.sam, a.display_name, a.kind, _yn(a.enabled), ",".join(a.spn) or "—"],
        inspect=lambda a, b: [
            ("SAM", a.sam),
            ("Name", a.display_name),
            ("Kind", a.kind),
            ("OU", _ou_name(b, a.ou)),
            ("Enabled", _yn(a.enabled)),
            ("SPN", ", ".join(a.spn) or "—"),
            ("Description", a.description or "—"),
        ],
        key=lambda a: a.id,
    )
)
_register(
    ModuleSpec(
        id="ous",
        title="Organizational Units",
        columns=[Column(c) for c in ("Name", "DN", "Protected")],
        loader=lambda b, q: [o for o in b.list_ous() if not q or q.lower() in o.name.lower() or q.lower() in o.dn.lower()],
        row=lambda o: [o.name, o.dn, _yn(o.protected)],
        inspect=lambda o, b: [("Name", o.name), ("DN", o.dn), ("Parent", o.parent_id or "—"), ("Protected", _yn(o.protected)), ("Description", o.description or "—")],
        key=lambda o: o.id,
        actions=[
            ActionSpec(
                "new",
                "Create OU",
                needs_selection=False,
                fields=[
                    FieldSpec("name", "Name"),
                    FieldSpec("parent_id", "Parent OU id", default="ou-users"),
                    FieldSpec("description", "Description"),
                ],
            )
        ],
    )
)
_register(
    ModuleSpec(
        id="dcs",
        title="Domain Controllers",
        columns=[Column(c) for c in ("Name", "Site", "IPv4", "GC", "Online", "FSMO")],
        loader=lambda b, q: [d for d in b.list_dcs() if not q or q.lower() in d.name.lower()],
        row=lambda d: [d.name, d.site, d.ipv4, _yn(d.gc), _yn(d.online), ",".join(d.fsmo) or "—"],
        inspect=lambda d, b: [
            ("Name", d.name),
            ("Site", d.site),
            ("IPv4", d.ipv4),
            ("OS", d.os),
            ("GC", _yn(d.gc)),
            ("RODC", _yn(d.rodcs)),
            ("Online", _yn(d.online)),
            ("FSMO", ", ".join(d.fsmo) or "—"),
        ],
        key=lambda d: d.id,
    )
)
_register(
    ModuleSpec(
        id="fsmo",
        title="FSMO Roles",
        columns=[Column(c) for c in ("Role", "Holder", "Scope")],
        loader=lambda b, q: [r for r in b.list_fsmo() if not q or q.lower() in r.role.lower()],
        row=lambda r: [r.role, r.holder, r.scope],
        inspect=lambda r, b: [("Role", r.role), ("Holder", r.holder), ("Scope", r.scope)],
        key=lambda r: r.role,
    )
)
_register(
    ModuleSpec(
        id="sites",
        title="Sites",
        columns=[Column(c) for c in ("Name", "Location", "Subnets", "DCs")],
        loader=lambda b, q: [s for s in b.list_sites() if not q or q.lower() in s.name.lower()],
        row=lambda s: [s.name, s.location, ",".join(s.subnets), str(len(s.dc_ids))],
        inspect=lambda s, b: [("Name", s.name), ("Location", s.location), ("Subnets", ", ".join(s.subnets)), ("DCs", ", ".join(s.dc_ids) or "—")],
        key=lambda s: s.id,
    )
)
_register(
    ModuleSpec(
        id="gpos",
        title="GPOs",
        columns=[Column(c) for c in ("Name", "Target", "En", "Enforced", "Status")],
        loader=lambda b, q: [g for g in b.list_gpos() if not q or q.lower() in g.name.lower()],
        row=lambda g: [g.name, g.target_ou, _yn(g.enabled), _yn(g.enforced), g.status],
        inspect=lambda g, b: [
            ("Name", g.name),
            ("Target", g.target_ou),
            ("Enabled", _yn(g.enabled)),
            ("Enforced", _yn(g.enforced)),
            ("Status", g.status),
            ("WMI filter", g.wmi_filter or "—"),
        ],
        key=lambda g: g.id,
        actions=[
            ActionSpec("enable", "Enable / link"),
            ActionSpec("disable", "Disable / unlink", destructive=True, confirm="Unlink this GPO?"),
        ],
    )
)
_register(
    ModuleSpec(
        id="replication",
        title="Replication",
        columns=[Column(c) for c in ("Source", "Dest", "NC", "Last success", "Fails")],
        loader=lambda b, q: [r for r in b.list_replication() if not q or q.lower() in f"{r.source} {r.dest}".lower()],
        row=lambda r: [r.source, r.dest, r.naming_context, _dt(r.last_success), str(r.fails)],
        inspect=lambda r, b: [
            ("Source", r.source),
            ("Dest", r.dest),
            ("Naming context", r.naming_context),
            ("Last success", _dt(r.last_success)),
            ("Fails", str(r.fails)),
        ],
        key=lambda r: f"{r.source}->{r.dest}:{r.naming_context}",
    )
)
_register(
    ModuleSpec(
        id="trusts",
        title="Trusts",
        columns=[Column(c) for c in ("Remote", "Direction", "Kind", "Transitive", "Healthy")],
        loader=lambda b, q: [t for t in b.list_trusts() if not q or q.lower() in t.remote.lower()],
        row=lambda t: [t.remote, t.direction, t.kind, _yn(t.transitive), _yn(t.healthy)],
        inspect=lambda t, b: [
            ("Remote", t.remote),
            ("Direction", t.direction),
            ("Kind", t.kind),
            ("Transitive", _yn(t.transitive)),
            ("Healthy", _yn(t.healthy)),
        ],
        key=lambda t: t.id,
    )
)
_register(
    ModuleSpec(
        id="mailboxes",
        title="Mailboxes",
        columns=[Column(c) for c in ("Name", "Alias", "Type", "SMTP", "Lic", "Quota", "Hold")],
        loader=lambda b, q: b.list_mailboxes(q),
        row=_mb_row,
        inspect=_mb_inspect,
        key=lambda m: m.id,
        actions=_mailbox_actions(),
    )
)
def _load_permissions(backend: Any, query: str) -> list[Any]:
    boxes = {m.id: m for m in backend.list_mailboxes()}
    rows: list[Any] = []
    for perm in backend.list_permissions():
        mb = boxes.get(perm.mailbox_id)
        alias = mb.alias if mb else perm.mailbox_id
        smtp = mb.primary_smtp if mb else ""
        blob = f"{alias} {smtp} {perm.trustee} {perm.trustee_name} {perm.rights.value}"
        if query and query.lower() not in blob.lower():
            continue
        rows.append(
            SimpleNamespace(
                id=perm.id,
                mailbox_id=perm.mailbox_id,
                alias=alias,
                smtp=smtp,
                trustee=perm.trustee,
                trustee_name=perm.trustee_name,
                rights=perm.rights,
                automapping=perm.automapping,
                calendar_level=perm.calendar_level,
            )
        )
    return rows


_register(
    ModuleSpec(
        id="permissions",
        title="Mailbox Permissions",
        columns=[Column(c) for c in ("Mailbox", "Trustee", "Rights", "Automap", "Calendar")],
        loader=_load_permissions,
        row=lambda p: [
            p.alias,
            p.trustee_name,
            p.rights.value,
            _yn(p.automapping),
            p.calendar_level or "—",
        ],
        inspect=lambda p, b: [
            ("Mailbox", p.smtp or p.alias),
            ("Trustee", p.trustee),
            ("Trustee name", p.trustee_name),
            ("Rights", p.rights.value),
            ("Automapping", _yn(p.automapping)),
            ("Calendar", p.calendar_level or "—"),
        ],
        key=lambda p: p.id,
        actions=[
            ActionSpec(
                "grant",
                "Grant permission",
                needs_selection=False,
                fields=[
                    FieldSpec("mailbox_id", "Mailbox id or alias"),
                    FieldSpec("trustee", "Trustee UPN"),
                    FieldSpec("rights", "Rights", kind="select", options=RIGHT_OPTS, default="FullAccess"),
                    FieldSpec("automapping", "Automapping (Y/n)", default="Y"),
                ],
            ),
            ActionSpec("revoke", "Revoke", destructive=True, confirm="Revoke this permission?"),
        ],
    )
)


def _load_recipients(backend: Any, query: str) -> list[Any]:
    items: list[Any] = list(backend.list_mailboxes(query))
    items.extend([g for g in backend.list_groups(query) if g.mail])
    return items


def _recipient_row(obj: Any) -> list[str]:
    if isinstance(obj, Mailbox):
        return [obj.display_name, obj.primary_smtp, obj.mailbox_type.value, "mailbox"]
    if isinstance(obj, Group):
        return [obj.name, obj.mail or "—", obj.group_type.value, "group"]
    return [str(obj), "", "", ""]


def _recipient_inspect(obj: Any, backend: Any) -> list[tuple[str, str]]:
    if isinstance(obj, Mailbox):
        return _mb_inspect(obj, backend)
    if isinstance(obj, Group):
        return [("Name", obj.name), ("Mail", obj.mail or "—"), ("Type", obj.group_type.value), ("Members", str(len(obj.member_ids)))]
    return [("Object", str(obj))]


_register(
    ModuleSpec(
        id="recipients",
        title="Recipients",
        columns=[Column(c) for c in ("Name", "SMTP", "Type", "Kind")],
        loader=_load_recipients,
        row=_recipient_row,
        inspect=_recipient_inspect,
        key=lambda o: o.id,
    )
)
_register(
    ModuleSpec(
        id="distribution",
        title="Distribution",
        columns=[Column(c) for c in ("Name", "Type", "Mail", "Members")],
        loader=lambda b, q: [
            g
            for g in b.list_groups(q)
            if g.group_type in {GroupType.DISTRIBUTION, GroupType.MAIL_SECURITY, GroupType.M365}
        ],
        row=lambda g: [g.name, g.group_type.value, g.mail or "—", str(len(g.member_ids))],
        inspect=lambda g, b: [
            ("Name", g.name),
            ("Type", g.group_type.value),
            ("Mail", g.mail or "—"),
            ("Members", str(len(g.member_ids))),
            ("Origin", g.origin.value),
        ],
        key=lambda g: g.id,
        actions=[
            ActionSpec("add_member", "Add member", fields=[FieldSpec("member_id", "User id or UPN")]),
            ActionSpec("remove_member", "Remove member", fields=[FieldSpec("member_id", "User id or UPN")]),
        ],
    )
)
_register(
    ModuleSpec(
        id="resources",
        title="Shared / Resources",
        columns=[Column(c) for c in ("Name", "Alias", "Type", "SMTP", "Quota")],
        loader=lambda b, q: [
            m
            for m in b.list_mailboxes(q)
            if m.mailbox_type in {MailboxType.SHARED, MailboxType.ROOM, MailboxType.EQUIPMENT}
        ],
        row=lambda m: [m.display_name, m.alias, m.mailbox_type.value, m.primary_smtp, f"{m.used_gb:.0f}/{m.quota_gb:.0f}G"],
        inspect=_mb_inspect,
        key=lambda m: m.id,
        actions=_mailbox_actions(),
    )
)
_register(
    ModuleSpec(
        id="mailflow",
        title="Mail Flow",
        columns=[Column(c) for c in ("Name", "Direction", "Status", "Host")],
        loader=lambda b, q: [c for c in b.list_mail_flow() if not q or q.lower() in c.name.lower()],
        row=lambda c: [c.name, c.direction, c.status, c.smart_host or c.host],
        inspect=lambda c, b: [("Name", c.name), ("Direction", c.direction), ("Status", c.status), ("Host", c.host), ("Smart host", c.smart_host or "—")],
        key=lambda c: c.id,
    )
)
_register(
    ModuleSpec(
        id="cloud_users",
        title="Cloud Users",
        columns=[Column(c) for c in ("Name", "UPN", "Origin", "Licenses", "Enabled")],
        loader=lambda b, q: b.list_cloud_users(q),
        row=lambda u: [u.display_name, u.upn, u.origin.value, ",".join(u.licenses) or "—", _yn(u.enabled)],
        inspect=_user_inspect,
        key=lambda u: u.id,
        actions=_user_actions(),
    )
)
_register(
    ModuleSpec(
        id="guests",
        title="Guests",
        columns=[Column(c) for c in ("Name", "UPN", "Enabled", "Mail")],
        loader=lambda b, q: b.list_guests(q),
        row=lambda u: [u.display_name, u.upn, _yn(u.enabled), u.mail or "—"],
        inspect=_user_inspect,
        key=lambda u: u.id,
        actions=[
            ActionSpec("disable", "Disable guest", destructive=True, confirm="Disable this guest?"),
            ActionSpec("enable", "Enable guest"),
        ],
    )
)
_register(
    ModuleSpec(
        id="licenses",
        title="Licenses",
        columns=[Column(c) for c in ("SKU", "Name", "Total", "Consumed", "Available")],
        loader=lambda b, q: [s for s in b.list_licenses() if not q or q.lower() in f"{s.sku} {s.name}".lower()],
        row=lambda s: [s.sku, s.name, str(s.total), str(s.consumed), str(s.available)],
        inspect=lambda s, b: [("SKU", s.sku), ("Name", s.name), ("Total", str(s.total)), ("Consumed", str(s.consumed)), ("Available", str(s.available))],
        key=lambda s: s.sku,
        actions=[
            ActionSpec(
                "assign_license",
                "Assign to user",
                needs_selection=True,
                fields=[FieldSpec("user_id", "User id or UPN")],
            ),
            ActionSpec(
                "remove_license",
                "Remove from user",
                needs_selection=True,
                fields=[FieldSpec("user_id", "User id or UPN")],
            ),
        ],
    )
)
_register(
    ModuleSpec(
        id="roles",
        title="Directory Roles",
        columns=[Column(c) for c in ("Role", "Members")],
        loader=lambda b, q: [r for r in b.list_roles() if not q or q.lower() in r.name.lower()],
        row=lambda r: [r.name, str(len(r.member_ids))],
        inspect=lambda r, b: [
            ("Role", r.name),
            ("Members", str(len(r.member_ids))),
            (
                "People",
                ", ".join(
                    next((u.display_name for u in b.list_users() if u.id == mid), mid) for mid in r.member_ids
                )
                or "—",
            ),
        ],
        key=lambda r: r.id,
    )
)
_register(
    ModuleSpec(
        id="softdeleted",
        title="Soft-Deleted",
        columns=[Column(c) for c in ("Name", "UPN", "Kind", "Deleted", "Days left")],
        loader=lambda b, q: [s for s in b.list_soft_deleted() if not q or q.lower() in f"{s.display_name} {s.upn}".lower()],
        row=lambda s: [s.display_name, s.upn, s.kind, _dt(s.deleted), str(s.days_remaining)],
        inspect=lambda s, b: [
            ("Name", s.display_name),
            ("UPN", s.upn),
            ("Kind", s.kind),
            ("Deleted", _dt(s.deleted)),
            ("Days remaining", str(s.days_remaining)),
        ],
        key=lambda s: s.id,
        actions=[ActionSpec("restore", "Restore", confirm="Restore this object from the recycle bin?")],
    )
)
_register(
    ModuleSpec(
        id="locks",
        title="Locks / Passwords",
        columns=[Column(c) for c in ("Name", "UPN", "Locked", "Enabled", "Must change")],
        loader=lambda b, q: [
            u
            for u in b.list_users(q)
            if u.locked or not u.enabled or u.must_change_password
        ],
        row=lambda u: [u.display_name, u.upn, _yn(u.locked), _yn(u.enabled), _yn(u.must_change_password)],
        inspect=_user_inspect,
        key=lambda u: u.id,
        actions=[
            ActionSpec("unlock", "Unlock"),
            ActionSpec("enable", "Enable"),
            ActionSpec("reset_password", "Reset password", destructive=True, confirm="Issue a temporary password?"),
        ],
    )
)
_register(
    ModuleSpec(
        id="privileged",
        title="Privileged Access",
        columns=[Column(c) for c in ("Group", "Type", "Members", "Origin")],
        loader=lambda b, q: [g for g in b.list_groups(q) if g.privileged],
        row=lambda g: [g.name, g.group_type.value, str(len(g.member_ids)), g.origin.value],
        inspect=lambda g, b: [
            ("Name", g.name),
            ("Privileged", _yn(g.privileged)),
            ("Members", str(len(g.member_ids))),
            (
                "People",
                ", ".join(
                    next((u.display_name for u in b.list_users() if u.id == mid), mid) for mid in g.member_ids
                )
                or "—",
            ),
        ],
        key=lambda g: g.id,
        actions=[
            ActionSpec("add_member", "Add member", fields=[FieldSpec("member_id", "User id or UPN")]),
            ActionSpec(
                "remove_member",
                "Remove member",
                destructive=True,
                confirm="Remove this member from a privileged group?",
                fields=[FieldSpec("member_id", "User id or UPN")],
            ),
        ],
    )
)
_register(
    ModuleSpec(
        id="jobs",
        title="Jobs",
        columns=[Column(c) for c in ("When", "Action", "Target", "Status", "Message")],
        loader=lambda b, q: [j for j in b.list_jobs() if not q or q.lower() in f"{j.action} {j.target} {j.message}".lower()],
        row=lambda j: [_dt(j.created), j.action, j.target, j.status, j.message[:40]],
        inspect=lambda j, b: [("Action", j.action), ("Target", j.target), ("Status", j.status), ("When", _dt(j.created)), ("Message", j.message)],
        key=lambda j: j.id,
    )
)
_register(
    ModuleSpec(
        id="audit",
        title="Audit Log",
        columns=[Column(c) for c in ("When", "Actor", "Action", "Target", "Detail")],
        loader=lambda b, q: [a for a in b.list_audit() if not q or q.lower() in f"{a.action} {a.target} {a.detail}".lower()],
        row=lambda a: [_dt(a.at), a.actor, a.action, a.target, a.detail[:40]],
        inspect=lambda a, b: [("Actor", a.actor), ("Action", a.action), ("Target", a.target), ("When", _dt(a.at)), ("Detail", a.detail)],
        key=lambda a: a.id,
    )
)
_register(
    ModuleSpec(
        id="connectors",
        title="Connectors",
        columns=[Column(c) for c in ("Name", "Kind", "Health", "Live", "Detail")],
        loader=lambda b, q: [c for c in b.connector_status() if not q or q.lower() in c.name.lower()],
        row=lambda c: [c.name, c.kind, c.health, _yn(c.live), c.detail],
        inspect=lambda c, b: [("Name", c.name), ("Kind", c.kind), ("Health", c.health), ("Live", _yn(c.live)), ("Detail", c.detail)],
        key=lambda c: c.name,
        actions=[
            ActionSpec("login", "Sign in (LDAP + Graph login)", needs_selection=False),
        ],
    )
)

JUMP_ALIASES: dict[str, str] = {}
for _section, items in NAV:
    for mid, label in items:
        JUMP_ALIASES[mid] = mid
        JUMP_ALIASES[label.lower()] = mid
JUMP_ALIASES.update(
    {
        "dashboard": "dashboard",
        "home": "dashboard",
        "user": "users",
        "mbx": "mailboxes",
        "mail": "mailboxes",
        "perms": "permissions",
        "acl": "permissions",
        "sync": "aadconnect",
        "aad": "aadconnect",
        "exo": "mailboxes",
        "gpo": "gpos",
        "dc": "dcs",
        "ou": "ous",
        "job": "jobs",
        "log": "audit",
        "guest": "guests",
        "license": "licenses",
        "role": "roles",
        "lock": "locks",
        "priv": "privileged",
        "setting": "settings",
        "config": "settings",
        "login": "connectors",
        "flow": "mailflow",
        "dl": "distribution",
        "shared": "resources",
        "room": "resources",
    }
)


def resolve_jump(text: str) -> str | None:
    key = text.strip().lower()
    if key in JUMP_ALIASES:
        return JUMP_ALIASES[key]
    for alias, mid in JUMP_ALIASES.items():
        if key in alias or alias in key:
            return mid
    return None
