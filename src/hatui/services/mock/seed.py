from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from hatui.models import (
    Alert,
    AuditEvent,
    Computer,
    ConnectorStatus,
    Contact,
    DirectoryRole,
    DomainController,
    ForestHealth,
    FsmoRole,
    GpoLink,
    Group,
    GroupType,
    HealthState,
    Job,
    LicenseSku,
    Mailbox,
    MailboxPermission,
    MailboxRight,
    MailboxType,
    MailFlowConnector,
    OrgUnit,
    Origin,
    ReplicationPartner,
    ServiceAccount,
    Site,
    SoftDeleted,
    SyncStatus,
    Trust,
    User,
)

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _ago(hours: float = 0, days: float = 0) -> datetime:
    return _now() - timedelta(hours=hours, days=days)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


class Store:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.groups: dict[str, Group] = {}
        self.computers: dict[str, Computer] = {}
        self.contacts: dict[str, Contact] = {}
        self.service_accounts: dict[str, ServiceAccount] = {}
        self.ous: dict[str, OrgUnit] = {}
        self.dcs: dict[str, DomainController] = {}
        self.fsmo: list[FsmoRole] = []
        self.sites: dict[str, Site] = {}
        self.gpos: dict[str, GpoLink] = {}
        self.replication: list[ReplicationPartner] = []
        self.trusts: dict[str, Trust] = {}
        self.mailboxes: dict[str, Mailbox] = {}
        self.permissions: dict[str, MailboxPermission] = {}
        self.mail_flow: dict[str, MailFlowConnector] = {}
        self.licenses: dict[str, LicenseSku] = {}
        self.roles: dict[str, DirectoryRole] = {}
        self.soft_deleted: dict[str, SoftDeleted] = {}
        self.jobs: list[Job] = []
        self.audit: list[AuditEvent] = []
        self.sync = SyncStatus()
        self.connectors: list[ConnectorStatus] = []
        self.domain = "blackrainlabs.corp"
        self.tenant = "blackrainlabs.onmicrosoft.com"


CAST = [
    ("Elena", "Voss", "Security", "Director of Identity", "HQ", Origin.SYNCED),
    ("Marcus", "Hale", "Security", "SOC Lead", "HQ", Origin.SYNCED),
    ("Nyx", "Calder", "Engineering", "Principal Engineer", "HQ", Origin.SYNCED),
    ("Ivy", "Okoye", "Engineering", "Hybrid Identity Architect", "DC1", Origin.SYNCED),
    ("Jonah", "Reeves", "Operations", "Directory Operator", "DC1", Origin.SYNCED),
    ("Sable", "Quinn", "Executive", "CIO", "HQ", Origin.SYNCED),
    ("Theo", "Marsh", "Finance", "Controller", "HQ", Origin.SYNCED),
    ("Rina", "Sato", "Legal", "Counsel", "HQ", Origin.SYNCED),
    ("Wes", "Phelan", "Helpdesk", "Tier 3", "DC2", Origin.ONPREM),
    ("Amina", "Darzi", "HR", "People Ops", "HQ", Origin.SYNCED),
    ("Cole", "Varga", "Research", "Lab Admin", "DC2", Origin.ONPREM),
    ("Pax", "Ortega", "Facilities", "Site Lead", "DC1", Origin.ONPREM),
    ("Lumen", "Cho", "Engineering", "Exchange Engineer", "Cloud", Origin.CLOUD_ONLY),
    ("Gia", "North", "Security", "PAM Analyst", "HQ", Origin.SYNCED),
    ("Bram", "Keller", "Operations", "AAD Connect Admin", "DC1", Origin.SYNCED),
    ("Eden", "Frost", "Engineering", "M365 Engineer", "Cloud", Origin.CLOUD_ONLY),
    ("Kade", "Morrow", "Helpdesk", "Tier 2", "DC2", Origin.SYNCED),
    ("Vera", "Solis", "Executive", "CISO", "HQ", Origin.SYNCED),
    ("Nico", "Adler", "Finance", "AP Lead", "HQ", Origin.SYNCED),
    ("Wren", "Ibarra", "Research", "Data Steward", "DC2", Origin.SYNCED),
]

FIRST = [
    "Ava", "Noah", "Mia", "Leo", "Zoe", "Kai", "Nora", "Eli", "Quinn", "Jade",
    "Hugo", "Iris", "Owen", "Lyra", "Felix", "Sage", "Remy", "Cora", "Axel", "Dina",
    "Nia", "Omar", "Pia", "Rafi", "Tessa", "Uma", "Vic", "Willa", "Yuri", "Zane",
    "Beau", "Cleo", "Drew", "Esme", "Finn", "Greta", "Hale", "Indi", "Jules", "Kira",
    "Lane", "Mara", "Nash", "Opal", "Penn", "Rosa", "Shea", "Tess", "Uri", "Vale",
    "Wynn", "Xan", "Yael", "Zora", "Arlo", "Blair", "Cass", "Dell", "Echo", "Ford",
]
LAST = [
    "Vance", "Bishop", "Crowe", "Dunn", "Ellis", "Ford", "Grant", "Hayes", "Ingram",
    "Joss", "Keene", "Lang", "Morse", "Nash", "Owen", "Pike", "Rhodes", "Shaw",
    "Tate", "Ulrich", "Vale", "Wade", "Xu", "Young", "Zimm", "Ash", "Beck", "Cole",
]
DEPTS = [
    ("Engineering", "Engineer"),
    ("Security", "Analyst"),
    ("Finance", "Analyst"),
    ("Operations", "Operator"),
    ("Legal", "Paralegal"),
    ("HR", "Coordinator"),
    ("Facilities", "Technician"),
    ("Helpdesk", "Specialist"),
    ("Research", "Scientist"),
    ("Executive", "Advisor"),
]
OFFICES = ["HQ", "DC1", "DC2", "Cloud"]


def _upn(given: str, surname: str, domain: str) -> str:
    return f"{given}.{surname}@{domain}".lower()


def _sam(given: str, surname: str) -> str:
    return f"{given[0]}{surname}".lower()[:20]


def seed_store() -> Store:
    s = Store()
    domain = s.domain
    tenant = s.tenant

    ou_corp = OrgUnit(id="ou-corp", name="BlackRain", dn="OU=BlackRain,DC=blackrainlabs,DC=corp", protected=True)
    ou_users = OrgUnit(id="ou-users", name="Users", dn="OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-corp")
    ou_svc = OrgUnit(id="ou-svc", name="Service Accounts", dn="OU=Service Accounts,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-corp")
    ou_comp = OrgUnit(id="ou-comp", name="Computers", dn="OU=Computers,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-corp")
    ou_sec = OrgUnit(id="ou-sec", name="Security", dn="OU=Security,OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-users")
    ou_eng = OrgUnit(id="ou-eng", name="Engineering", dn="OU=Engineering,OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-users")
    ou_ops = OrgUnit(id="ou-ops", name="Operations", dn="OU=Operations,OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-users")
    ou_fin = OrgUnit(id="ou-fin", name="Finance", dn="OU=Finance,OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-users")
    ou_exec = OrgUnit(id="ou-exec", name="Executive", dn="OU=Executive,OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-users")
    ou_disabled = OrgUnit(id="ou-dis", name="Disabled", dn="OU=Disabled,OU=BlackRain,DC=blackrainlabs,DC=corp", parent_id="ou-corp")
    for ou in (ou_corp, ou_users, ou_svc, ou_comp, ou_sec, ou_eng, ou_ops, ou_fin, ou_exec, ou_disabled):
        s.ous[ou.id] = ou

    dept_ou = {
        "Security": "ou-sec",
        "Engineering": "ou-eng",
        "Operations": "ou-ops",
        "Finance": "ou-fin",
        "Executive": "ou-exec",
        "Legal": "ou-users",
        "HR": "ou-users",
        "Facilities": "ou-ops",
        "Helpdesk": "ou-ops",
        "Research": "ou-eng",
    }

    dc1 = DomainController(
        id="dc-1", name="BRL-DC01", site="HQ-Core", ipv4="10.8.1.11",
        fsmo=["Schema Master", "Domain Naming Master", "PDC Emulator"],
    )
    dc2 = DomainController(
        id="dc-2", name="BRL-DC02", site="HQ-Core", ipv4="10.8.1.12",
        fsmo=["RID Master", "Infrastructure Master"],
    )
    dc3 = DomainController(
        id="dc-3", name="BRL-DC03", site="DC1-Edge", ipv4="10.8.20.11", gc=True,
    )
    s.dcs = {d.id: d for d in (dc1, dc2, dc3)}
    s.fsmo = [
        FsmoRole(role="Schema Master", holder="BRL-DC01", scope="forest"),
        FsmoRole(role="Domain Naming Master", holder="BRL-DC01", scope="forest"),
        FsmoRole(role="PDC Emulator", holder="BRL-DC01", scope="domain"),
        FsmoRole(role="RID Master", holder="BRL-DC02", scope="domain"),
        FsmoRole(role="Infrastructure Master", holder="BRL-DC02", scope="domain"),
    ]
    s.sites = {
        "st-hq": Site(id="st-hq", name="HQ-Core", subnets=["10.8.1.0/24", "10.8.2.0/24"], location="BlackRain HQ", dc_ids=["dc-1", "dc-2"]),
        "st-e": Site(id="st-e", name="DC1-Edge", subnets=["10.8.20.0/24"], location="Edge Cage", dc_ids=["dc-3"]),
        "st-c": Site(id="st-c", name="Cloud-Transit", subnets=["10.90.0.0/16"], location="Azure", dc_ids=[]),
    }
    s.gpos = {
        "gpo-1": GpoLink(id="gpo-1", name="Default Domain Policy", target_ou="DC=blackrainlabs,DC=corp", enforced=True),
        "gpo-2": GpoLink(id="gpo-2", name="Workstation Baseline", target_ou="OU=Computers,OU=BlackRain,DC=blackrainlabs,DC=corp"),
        "gpo-3": GpoLink(id="gpo-3", name="Privileged Access", target_ou="OU=Security,OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", enforced=True),
        "gpo-4": GpoLink(id="gpo-4", name="Helpdesk Kiosk", target_ou="OU=Operations,OU=Users,OU=BlackRain,DC=blackrainlabs,DC=corp", enabled=False, status="unlinked"),
        "gpo-5": GpoLink(id="gpo-5", name="BitLocker HQ", target_ou="OU=Computers,OU=BlackRain,DC=blackrainlabs,DC=corp", wmi_filter="Laptops"),
    }
    s.replication = [
        ReplicationPartner(source="BRL-DC01", dest="BRL-DC02", last_success=_ago(hours=0.2), naming_context="DC=blackrainlabs,DC=corp"),
        ReplicationPartner(source="BRL-DC02", dest="BRL-DC01", last_success=_ago(hours=0.2), naming_context="DC=blackrainlabs,DC=corp"),
        ReplicationPartner(source="BRL-DC01", dest="BRL-DC03", last_success=_ago(hours=1.5), fails=1, naming_context="DC=blackrainlabs,DC=corp"),
        ReplicationPartner(source="BRL-DC03", dest="BRL-DC01", last_success=_ago(hours=0.4), naming_context="Configuration"),
    ]
    s.trusts = {
        "t-1": Trust(id="t-1", remote="blacksite.mil", direction="outbound", kind="external", transitive=False, healthy=True),
        "t-2": Trust(id="t-2", remote="partner.orbit", direction="bidirectional", kind="forest", healthy=True),
    }

    groups_spec = [
        ("g-da", "Domain Admins", "DomainAdmins", GroupType.SECURITY, True),
        ("g-ea", "Enterprise Admins", "EnterpriseAdmins", GroupType.SECURITY, True),
        ("g-schema", "Schema Admins", "SchemaAdmins", GroupType.SECURITY, True),
        ("g-exrec", "Exchange Recipients", "ExchangeRecipients", GroupType.MAIL_SECURITY, False),
        ("g-exorg", "Organization Management", "OrgMgmt", GroupType.SECURITY, True),
        ("g-help", "Helpdesk", "Helpdesk", GroupType.SECURITY, False),
        ("g-sec", "Security Ops", "SecOps", GroupType.SECURITY, False),
        ("g-eng", "Engineering", "Engineering", GroupType.SECURITY, False),
        ("g-all", "All Staff", "AllStaff", GroupType.DISTRIBUTION, False),
        ("g-exec", "Executives", "Executives", GroupType.DISTRIBUTION, False),
        ("g-m365-sec", "SecOps Team", "SecOpsTeam", GroupType.M365, False),
        ("g-m365-eng", "Engineering Hub", "EngHub", GroupType.M365, False),
        ("g-shared-fin", "Finance Shared", "FinShared", GroupType.MAIL_SECURITY, False),
        ("g-guests", "Guest Access", "GuestAccess", GroupType.SECURITY, False),
        ("g-priv", "Privileged Role Admins", "PrivRoleAdmins", GroupType.SECURITY, True),
    ]
    for gid, name, sam, gtype, priv in groups_spec:
        mail = f"{sam.lower()}@{domain}" if gtype != GroupType.SECURITY else None
        if gtype == GroupType.M365:
            mail = f"{sam.lower()}@{tenant}"
        s.groups[gid] = Group(
            id=gid, name=name, sam=sam, mail=mail, group_type=gtype,
            ou="ou-sec" if priv else "ou-users", privileged=priv,
            origin=Origin.CLOUD_ONLY if gtype == GroupType.M365 else Origin.SYNCED,
            description=name,
        )

    s.licenses = {
        "E3": LicenseSku(sku="SPE_E3", name="Microsoft 365 E3", total=80, consumed=0, available=80),
        "E5": LicenseSku(sku="SPE_E5", name="Microsoft 365 E5", total=15, consumed=0, available=15),
        "EXO": LicenseSku(sku="EXCHANGESTANDARD", name="Exchange Online P1", total=20, consumed=0, available=20),
        "P2": LicenseSku(sku="AAD_PREMIUM_P2", name="Entra ID P2", total=30, consumed=0, available=30),
    }

    def add_user(
        given: str,
        surname: str,
        dept: str,
        title: str,
        office: str,
        origin: Origin,
        *,
        enabled: bool = True,
        locked: bool = False,
        mailbox: bool = True,
        mtype: MailboxType | None = None,
        license_sku: str | None = "E3",
        extra_groups: list[str] | None = None,
        sync_error: str | None = None,
        guest: bool = False,
    ) -> User:
        uid = _id("u")
        sam = _sam(given, surname)
        n = 2
        while any(u.sam == sam for u in s.users.values()):
            sam = f"{_sam(given, surname)}{n}"
            n += 1
        upn_domain = tenant if origin == Origin.CLOUD_ONLY or guest else domain
        upn = _upn(given, surname, upn_domain)
        if guest:
            upn = f"{given.lower()}.{surname.lower()}#EXT#@{tenant}"
        mail = None if not mailbox else (f"{given}.{surname}@{domain}".lower() if not guest else f"{given}.{surname}@partner.orbit".lower())
        licenses: list[str] = []
        if license_sku and origin != Origin.ONPREM and not guest and mailbox:
            sku = s.licenses[license_sku]
            if sku.available > 0:
                sku.consumed += 1
                sku.available -= 1
                licenses = [sku.sku]
        user = User(
            id=uid,
            sam=sam,
            upn=upn,
            display_name=f"{given} {surname}",
            given_name=given,
            surname=surname,
            mail=mail,
            department=dept,
            title=title,
            office=office,
            ou=dept_ou.get(dept, "ou-users") if enabled else "ou-dis",
            enabled=enabled,
            locked=locked,
            origin=origin,
            immutable_id=None if origin == Origin.CLOUD_ONLY else f"imm-{sam}",
            last_sync=_ago(hours=1) if origin == Origin.SYNCED else None,
            last_logon=_ago(hours=3) if enabled else _ago(days=40),
            employee_id=f"AD-{len(s.users)+1:04d}",
            proxy_addresses=[f"SMTP:{mail}"] if mail else [],
            licenses=licenses,
            group_ids=["g-all"] if not guest else ["g-guests"],
            guest=guest,
            sync_error=sync_error,
        )
        s.users[uid] = user
        s.groups["g-all"].member_ids.append(uid)
        if extra_groups:
            for gid in extra_groups:
                if gid in s.groups:
                    s.groups[gid].member_ids.append(uid)
                    user.group_ids.append(gid)
        if mailbox and not guest:
            mb_type = mtype or (
                MailboxType.USER if origin == Origin.CLOUD_ONLY else MailboxType.REMOTE
            )
            mid = _id("mb")
            licensed = bool(licenses) or origin == Origin.ONPREM
            mb = Mailbox(
                id=mid,
                alias=sam,
                primary_smtp=mail or f"{sam}@{domain}",
                display_name=user.display_name,
                mailbox_type=mb_type,
                user_id=uid,
                quota_gb=100.0 if license_sku == "E5" else 50.0,
                used_gb=round((hash(sam) % 400) / 10, 1),
                licensed=licensed,
                recipient_type=mb_type.value,
                database="EXO" if mb_type != MailboxType.USER or origin != Origin.ONPREM else "MBX-DB01",
                created=_ago(days=hash(sam) % 400),
                archive=license_sku == "E5",
            )
            user.mailbox_id = mid
            s.mailboxes[mid] = mb
            s.groups["g-exrec"].member_ids.append(uid)
            if "g-exrec" not in user.group_ids:
                user.group_ids.append("g-exrec")
        return user

    core_groups = {
        "Elena Voss": ["g-da", "g-ea", "g-priv", "g-sec", "g-exorg"],
        "Vera Solis": ["g-da", "g-priv", "g-sec"],
        "Sable Quinn": ["g-exec", "g-priv"],
        "Marcus Hale": ["g-sec", "g-exorg"],
        "Ivy Okoye": ["g-eng", "g-exorg"],
        "Nyx Calder": ["g-eng", "g-m365-eng"],
        "Bram Keller": ["g-ops"] if False else ["g-help"],
        "Jonah Reeves": ["g-help"],
        "Gia North": ["g-sec", "g-priv"],
        "Lumen Cho": ["g-eng", "g-m365-eng", "g-exorg"],
        "Eden Frost": ["g-eng", "g-m365-eng"],
        "Wes Phelan": ["g-help"],
        "Theo Marsh": ["g-shared-fin"],
        "Nico Adler": ["g-shared-fin"],
    }

    for given, surname, dept, title, office, origin in CAST:
        extras = core_groups.get(f"{given} {surname}", [])
        sku = "E5" if dept in {"Executive", "Security"} else "E3"
        if origin == Origin.ONPREM:
            sku = None
        add_user(given, surname, dept, title, office, origin, extra_groups=extras, license_sku=sku)

    # Named edge cases
    add_user("Locke", "Dray", "Helpdesk", "Contractor", "DC2", Origin.SYNCED, locked=True, license_sku="EXO")
    add_user("Dormant", "Wells", "Engineering", "Alumni", "HQ", Origin.SYNCED, enabled=False, mailbox=False, license_sku=None)
    add_user("Orphan", "Mail", "Operations", "Shared Owner", "HQ", Origin.SYNCED, mailbox=True, license_sku=None)
    add_user("Drift", "Sync", "Engineering", "Broken Anchor", "Cloud", Origin.SYNCED, sync_error="hard-match conflict: ImmutableId")
    add_user("Guest", "Liaison", "Operations", "Partner", "Cloud", Origin.CLOUD_ONLY, guest=True, mailbox=False, license_sku=None)

    idx = 0
    while len(s.users) < 82:
        given = FIRST[idx % len(FIRST)]
        surname = LAST[(idx * 3) % len(LAST)]
        dept, title = DEPTS[idx % len(DEPTS)]
        office = OFFICES[idx % len(OFFICES)]
        origin = Origin.CLOUD_ONLY if office == "Cloud" and idx % 5 == 0 else Origin.SYNCED
        extras = ["g-eng"] if dept == "Engineering" else ["g-sec"] if dept == "Security" else []
        add_user(given, surname, dept, title, office, origin, extra_groups=extras)
        idx += 1

    # Shared / resource mailboxes
    for alias, display, mtype in [
        ("finance", "Finance Shared", MailboxType.SHARED),
        ("helpdesk", "Helpdesk Shared", MailboxType.SHARED),
        ("secinbox", "Security Inbox", MailboxType.SHARED),
        ("boardroom", "Board Room", MailboxType.ROOM),
        ("warroom", "War Room", MailboxType.ROOM),
        ("projector", "HQ Projector", MailboxType.EQUIPMENT),
        ("fleetvan", "Facilities Van", MailboxType.EQUIPMENT),
    ]:
        mid = _id("mb")
        smtp = f"{alias}@{domain}"
        s.mailboxes[mid] = Mailbox(
            id=mid, alias=alias, primary_smtp=smtp, display_name=display,
            mailbox_type=mtype, user_id=None, quota_gb=50, used_gb=4.2,
            licensed=mtype == MailboxType.SHARED, recipient_type=mtype.value,
            created=_ago(days=200),
        )

    # Permissions
    def perm(mb_alias: str, trustee_upn: str, rights: MailboxRight, automap: bool = True) -> None:
        mb = next(m for m in s.mailboxes.values() if m.alias == mb_alias)
        trustee = next((u for u in s.users.values() if u.upn == trustee_upn), None)
        name = trustee.display_name if trustee else trustee_upn
        pid = _id("p")
        s.permissions[pid] = MailboxPermission(
            id=pid, mailbox_id=mb.id, trustee=trustee_upn, trustee_name=name,
            rights=rights, automapping=automap,
            calendar_level="Editor" if rights == MailboxRight.CALENDAR else None,
        )

    elena = next(u for u in s.users.values() if u.display_name == "Elena Voss")
    marcus = next(u for u in s.users.values() if u.display_name == "Marcus Hale")
    ivy = next(u for u in s.users.values() if u.display_name == "Ivy Okoye")
    lumen = next(u for u in s.users.values() if u.display_name == "Lumen Cho")
    theo = next(u for u in s.users.values() if u.display_name == "Theo Marsh")
    perm("finance", theo.upn, MailboxRight.FULL_ACCESS)
    perm("finance", theo.upn, MailboxRight.SEND_AS, automap=False)
    perm("helpdesk", next(u for u in s.users.values() if u.display_name == "Jonah Reeves").upn, MailboxRight.FULL_ACCESS)
    perm("secinbox", elena.upn, MailboxRight.FULL_ACCESS)
    perm("secinbox", marcus.upn, MailboxRight.SEND_AS, automap=False)
    perm("secinbox", marcus.upn, MailboxRight.SEND_ON_BEHALF, automap=False)
    if elena.mailbox_id:
        mb = s.mailboxes[elena.mailbox_id]
        pid = _id("p")
        s.permissions[pid] = MailboxPermission(
            id=pid, mailbox_id=mb.id, trustee=marcus.upn, trustee_name=marcus.display_name,
            rights=MailboxRight.CALENDAR, automapping=False, calendar_level="Reviewer",
        )
        pid = _id("p")
        s.permissions[pid] = MailboxPermission(
            id=pid, mailbox_id=mb.id, trustee=ivy.upn, trustee_name=ivy.display_name,
            rights=MailboxRight.FULL_ACCESS, automapping=True,
        )
    perm("boardroom", lumen.upn, MailboxRight.FULL_ACCESS, automap=False)

    # Computers
    for i, (name, os_, office) in enumerate([
        ("WS-VOSS-01", "Windows 11", "HQ"),
        ("WS-HALE-01", "Windows 11", "HQ"),
        ("LPT-OKOYE", "Windows 11", "DC1"),
        ("BRL-AAD01", "Windows Server 2022", "DC1"),
        ("BRL-EX01", "Windows Server 2022", "HQ"),
        ("KIOSK-HD01", "Windows 11 IoT", "DC2"),
    ]):
        cid = _id("c")
        s.computers[cid] = Computer(
            id=cid, name=name, sam=f"{name}$", os=os_,
            ou="ou-comp", last_logon=_ago(hours=i + 1),
            managed=name.startswith("WS") or name.startswith("LPT"),
            ip=f"10.8.{1 if office == 'HQ' else 20}.{20+i}",
        )
    for i in range(34):
        cid = _id("c")
        s.computers[cid] = Computer(
            id=cid, name=f"WS-{i+100:03d}", sam=f"WS-{i+100:03d}$",
            os="Windows 11" if i % 7 else "Windows 10",
            ou="ou-comp", last_logon=_ago(hours=i),
            managed=i % 3 != 0, ip=f"10.8.2.{i+10}",
        )

    s.contacts = {
        "ct-1": Contact(id="ct-1", display_name="Orbit Legal", mail="counsel@partner.orbit", company="Partner Orbit"),
        "ct-2": Contact(id="ct-2", display_name="Blacksite NOC", mail="noc@blacksite.mil", company="Blacksite"),
        "ct-3": Contact(id="ct-3", display_name="Vendor SOC", mail="soc@guard.example", company="Guard Co"),
    }
    s.service_accounts = {
        "sa-1": ServiceAccount(id="sa-1", sam="svc-aadconnect", display_name="AAD Connect", kind="user", ou="ou-svc", description="Azure AD Connect sync"),
        "sa-2": ServiceAccount(id="sa-2", sam="svc-backup$", display_name="Backup gMSA", kind="gMSA", ou="ou-svc", spn=["HOST/backup.blackrainlabs.corp"]),
        "sa-3": ServiceAccount(id="sa-3", sam="svc-exch", display_name="Exchange Health", kind="managed", ou="ou-svc", spn=["HTTP/mail.blackrainlabs.corp"]),
        "sa-4": ServiceAccount(id="sa-4", sam="svc-ldap-bind", display_name="BRL HATUI Bind", kind="user", ou="ou-svc"),
    }

    s.roles = {
        "r-ga": DirectoryRole(id="r-ga", name="Global Administrator", member_ids=[elena.id]),
        "r-ex": DirectoryRole(id="r-ex", name="Exchange Administrator", member_ids=[lumen.id, ivy.id]),
        "r-id": DirectoryRole(id="r-id", name="Identity Administrator", member_ids=[elena.id, ivy.id]),
        "r-hd": DirectoryRole(id="r-hd", name="Helpdesk Administrator", member_ids=[next(u.id for u in s.users.values() if u.display_name == "Jonah Reeves")]),
        "r-ub": DirectoryRole(id="r-ub", name="User Administrator", member_ids=[next(u.id for u in s.users.values() if u.display_name == "Kade Morrow")]),
    }
    s.soft_deleted = {
        "sd-1": SoftDeleted(id="sd-1", display_name="Riley Kant", upn=f"riley.kant@{domain}", deleted=_ago(days=4), days_remaining=26),
        "sd-2": SoftDeleted(id="sd-2", display_name="Temp Shared", upn=f"temp.shared@{domain}", kind="mailbox", deleted=_ago(days=12), days_remaining=18),
    }

    s.mail_flow = {
        "mf-1": MailFlowConnector(id="mf-1", name="Inbound from on-prem", direction="inbound", host="mail.blackrainlabs.corp"),
        "mf-2": MailFlowConnector(id="mf-2", name="Outbound to partner.orbit", direction="outbound", smart_host="mx.partner.orbit", host="partner.orbit"),
        "mf-3": MailFlowConnector(id="mf-3", name="Hybrid Centralized Transport", direction="outbound", status="enabled", host="BRL-EX01"),
    }

    s.sync = SyncStatus(
        last_delta=_ago(hours=0.5),
        last_full=_ago(days=3),
        exported=len([u for u in s.users.values() if u.origin == Origin.SYNCED]),
        errors=sum(1 for u in s.users.values() if u.sync_error),
        server="BRL-AAD01.blackrainlabs.corp",
    )
    s.connectors = [
        ConnectorStatus(name="Directory", kind="LDAP", live=False, detail="mock forest blackrainlabs.corp", health="MOCK"),
        ConnectorStatus(name="Entra / Graph", kind="Graph", live=False, detail="mock tenant blackrainlabs.onmicrosoft.com", health="MOCK"),
        ConnectorStatus(name="Exchange", kind="Graph", live=False, detail="mock EXO org", health="MOCK"),
        ConnectorStatus(name="AAD Connect", kind="Hybrid", live=False, detail=s.sync.server, health="MOCK"),
    ]

    s.jobs.append(Job(id=_id("j"), action="seed", target="forest", created=_ago(hours=6), message="BlackRainLabs mock forest loaded", status="ok"))
    s.audit.append(AuditEvent(id=_id("a"), at=_ago(hours=6), action="seed", target="blackrainlabs.corp", detail="mock org initialized"))
    return s


def forest_from(store: Store) -> ForestHealth:
    dcs = list(store.dcs.values())
    skus = list(store.licenses.values())
    alerts: list[Alert] = []
    if store.sync.errors:
        alerts.append(Alert(id="al-sync", severity="warn", source="AAD Connect", message=f"{store.sync.errors} sync error(s)"))
    repl_fail = sum(r.fails for r in store.replication)
    if repl_fail:
        alerts.append(Alert(id="al-repl", severity="warn", source="AD Replication", message=f"{repl_fail} replication fail(s) DC01→DC03"))
    locked = sum(1 for u in store.users.values() if u.locked)
    if locked:
        alerts.append(Alert(id="al-lock", severity="crit", source="Identity", message=f"{locked} locked account(s)"))
    unlic = sum(1 for m in store.mailboxes.values() if m.user_id and not m.licensed)
    if unlic:
        alerts.append(Alert(id="al-lic", severity="warn", source="Exchange", message=f"{unlic} unlicensed mailbox(es)"))
    alerts.append(Alert(id="al-ok", severity="ok", source="Forest", message="FSMO holders online"))
    return ForestHealth(
        forest="blackrainlabs.corp",
        domain=store.domain,
        forest_state=HealthState.HEALTHY,
        exo_state=HealthState.ONLINE,
        entra_state=HealthState.SYNCED if store.sync.errors == 0 else HealthState.DEGRADED,
        mode="MOCK",
        dc_online=sum(1 for d in dcs if d.online),
        dc_total=len(dcs),
        users=len(store.users),
        mailboxes=len(store.mailboxes),
        licenses_consumed=sum(x.consumed for x in skus),
        licenses_total=sum(x.total for x in skus),
        sync=store.sync.cycle,
        alerts=alerts,
    )
