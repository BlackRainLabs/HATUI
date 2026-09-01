from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from hatui.models import (
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
from hatui.services.mock.seed import Store, forest_from, seed_store
from hatui.services.protocol import HatuiError

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _matches(query: str, *parts: str | None) -> bool:
    if not query:
        return True
    blob = " ".join(p or "" for p in parts).lower()
    return query.lower() in blob


class MockBackend:
    def __init__(self, store: Store | None = None) -> None:
        self.store = store or seed_store()

    def _job(self, action: str, target: str, message: str = "", status: str = "ok") -> Job:
        job = Job(id=_id("j"), action=action, target=target, created=_now(), message=message, status=status)  # type: ignore[arg-type]
        self.store.jobs.insert(0, job)
        self.store.audit.insert(
            0,
            AuditEvent(id=_id("a"), at=_now(), action=action, target=target, detail=message),
        )
        return job

    def _user(self, user_id: str) -> User:
        try:
            return self.store.users[user_id]
        except KeyError as exc:
            raise HatuiError(f"user not found: {user_id}") from exc

    def list_users(self, query: str = "") -> list[User]:
        users = [u for u in self.store.users.values() if _matches(query, u.display_name, u.upn, u.sam, u.department, u.mail)]
        return sorted(users, key=lambda u: u.display_name.lower())

    def get_user(self, user_id: str) -> User:
        return self._user(user_id)

    def create_user(self, **fields: object) -> User:
        given = str(fields.get("given_name") or "")
        surname = str(fields.get("surname") or "")
        display = str(fields.get("display_name") or f"{given} {surname}".strip() or "New User")
        sam = str(fields.get("sam") or (f"{given[:1]}{surname}".lower() if given or surname else f"user{len(self.store.users)}"))
        origin = Origin(str(fields.get("origin") or Origin.SYNCED.value))
        domain = self.store.tenant if origin == Origin.CLOUD_ONLY else self.store.domain
        local = f"{given}.{surname}".lower() if given and surname else sam
        upn = str(fields.get("upn") or f"{local}@{domain}")
        uid = _id("u")
        user = User(
            id=uid,
            sam=sam,
            upn=upn,
            display_name=display,
            given_name=given,
            surname=surname,
            mail=str(fields.get("mail") or upn),
            department=str(fields.get("department") or ""),
            title=str(fields.get("title") or ""),
            office=str(fields.get("office") or "HQ"),
            ou=str(fields.get("ou") or "ou-users"),
            origin=origin,
            immutable_id=None if origin == Origin.CLOUD_ONLY else f"imm-{sam}",
            last_sync=_now() if origin == Origin.SYNCED else None,
            employee_id=f"AD-{len(self.store.users)+1:04d}",
            enabled=True,
        )
        self.store.users[uid] = user
        if "g-all" in self.store.groups:
            self.store.groups["g-all"].member_ids.append(uid)
            user.group_ids.append("g-all")
        self._job("create_user", user.upn, f"created {user.display_name} ({origin.value})")
        return user

    def set_user_enabled(self, user_id: str, enabled: bool) -> User:
        user = self._user(user_id)
        user.enabled = enabled
        if not enabled:
            user.ou = "ou-dis"
        self._job("enable" if enabled else "disable", user.upn, f"enabled={enabled}")
        return user

    def unlock_user(self, user_id: str) -> User:
        user = self._user(user_id)
        user.locked = False
        self._job("unlock", user.upn, "lockout cleared")
        return user

    def reset_password(self, user_id: str, temp: str, must_change: bool = True) -> User:
        user = self._user(user_id)
        user.must_change_password = must_change
        user.locked = False
        self._job("reset_password", user.upn, f"temp issued; must_change={must_change}")
        return user

    def move_user(self, user_id: str, ou_id: str) -> User:
        if ou_id not in self.store.ous:
            raise HatuiError(f"OU not found: {ou_id}")
        user = self._user(user_id)
        user.ou = ou_id
        self._job("move_user", user.upn, f"moved to {self.store.ous[ou_id].dn}")
        return user

    def list_groups(self, query: str = "") -> list[Group]:
        groups = [g for g in self.store.groups.values() if _matches(query, g.name, g.sam, g.mail, g.group_type.value)]
        return sorted(groups, key=lambda g: g.name.lower())

    def create_group(self, **fields: object) -> Group:
        name = str(fields.get("name") or "New Group")
        sam = str(fields.get("sam") or name.replace(" ", "")[:20])
        gtype = GroupType(str(fields.get("group_type") or GroupType.SECURITY.value))
        gid = _id("g")
        group = Group(
            id=gid,
            name=name,
            sam=sam,
            mail=str(fields["mail"]) if fields.get("mail") else None,
            group_type=gtype,
            ou=str(fields.get("ou") or "ou-users"),
            description=str(fields.get("description") or ""),
            origin=Origin.CLOUD_ONLY if gtype == GroupType.M365 else Origin.SYNCED,
        )
        self.store.groups[gid] = group
        self._job("create_group", group.name, gtype.value)
        return group

    def set_group_members(self, group_id: str, member_ids: list[str]) -> Group:
        group = self.store.groups[group_id]
        group.member_ids = list(member_ids)
        self._job("set_members", group.name, f"{len(member_ids)} members")
        return group

    def add_group_member(self, group_id: str, member_id: str) -> Group:
        group = self.store.groups[group_id]
        if member_id not in group.member_ids:
            group.member_ids.append(member_id)
        user = self.store.users.get(member_id)
        if user and group_id not in user.group_ids:
            user.group_ids.append(group_id)
        self._job("add_member", group.name, member_id)
        return group

    def remove_group_member(self, group_id: str, member_id: str) -> Group:
        group = self.store.groups[group_id]
        group.member_ids = [m for m in group.member_ids if m != member_id]
        user = self.store.users.get(member_id)
        if user:
            user.group_ids = [g for g in user.group_ids if g != group_id]
        self._job("remove_member", group.name, member_id)
        return group

    def list_computers(self, query: str = "") -> list[Computer]:
        comps = [c for c in self.store.computers.values() if _matches(query, c.name, c.os, c.ip)]
        return sorted(comps, key=lambda c: c.name.lower())

    def set_computer_enabled(self, computer_id: str, enabled: bool) -> Computer:
        comp = self.store.computers[computer_id]
        comp.enabled = enabled
        self._job("computer_enable" if enabled else "computer_disable", comp.name)
        return comp

    def list_contacts(self, query: str = "") -> list[Contact]:
        return [c for c in self.store.contacts.values() if _matches(query, c.display_name, c.mail, c.company)]

    def list_service_accounts(self, query: str = "") -> list[ServiceAccount]:
        return [a for a in self.store.service_accounts.values() if _matches(query, a.sam, a.display_name, a.kind)]

    def list_ous(self) -> list[OrgUnit]:
        return list(self.store.ous.values())

    def create_ou(self, name: str, parent_id: str | None, description: str = "") -> OrgUnit:
        parent = self.store.ous.get(parent_id) if parent_id else None
        dn = f"OU={name},{parent.dn}" if parent else f"OU={name},DC=blackrainlabs,DC=corp"
        ou = OrgUnit(id=_id("ou"), name=name, dn=dn, parent_id=parent_id, description=description)
        self.store.ous[ou.id] = ou
        self._job("create_ou", ou.dn)
        return ou

    def list_dcs(self) -> list[DomainController]:
        return list(self.store.dcs.values())

    def list_fsmo(self) -> list[FsmoRole]:
        return list(self.store.fsmo)

    def list_sites(self) -> list[Site]:
        return list(self.store.sites.values())

    def list_gpos(self) -> list[GpoLink]:
        return list(self.store.gpos.values())

    def set_gpo_enabled(self, gpo_id: str, enabled: bool) -> GpoLink:
        gpo = self.store.gpos[gpo_id]
        gpo.enabled = enabled
        gpo.status = "applied" if enabled else "unlinked"
        self._job("gpo_link" if enabled else "gpo_unlink", gpo.name)
        return gpo

    def list_replication(self) -> list[ReplicationPartner]:
        return list(self.store.replication)

    def list_trusts(self) -> list[Trust]:
        return list(self.store.trusts.values())

    def list_mailboxes(self, query: str = "") -> list[Mailbox]:
        boxes = [
            m
            for m in self.store.mailboxes.values()
            if _matches(query, m.alias, m.primary_smtp, m.display_name, m.mailbox_type.value)
        ]
        return sorted(boxes, key=lambda m: m.display_name.lower())

    def get_mailbox(self, mailbox_id: str) -> Mailbox:
        try:
            return self.store.mailboxes[mailbox_id]
        except KeyError as exc:
            raise HatuiError(f"mailbox not found: {mailbox_id}") from exc

    def create_mailbox(
        self,
        display_name: str,
        alias: str,
        mailbox_type: MailboxType,
        user_id: str | None = None,
    ) -> Mailbox:
        if any(m.alias.lower() == alias.lower() for m in self.store.mailboxes.values()):
            raise HatuiError(f"alias in use: {alias}")
        mid = _id("mb")
        smtp = f"{alias}@{self.store.domain}"
        mb = Mailbox(
            id=mid,
            alias=alias,
            primary_smtp=smtp,
            display_name=display_name,
            mailbox_type=mailbox_type,
            user_id=user_id,
            recipient_type=mailbox_type.value,
            created=_now(),
            licensed=mailbox_type in {MailboxType.USER, MailboxType.REMOTE, MailboxType.SHARED},
        )
        self.store.mailboxes[mid] = mb
        if user_id:
            user = self._user(user_id)
            user.mailbox_id = mid
            user.mail = smtp
        self._job("create_mailbox", smtp, mailbox_type.value)
        return mb

    def enable_mailbox(self, user_id: str, mailbox_type: MailboxType | None = None) -> Mailbox:
        user = self._user(user_id)
        if user.mailbox_id and user.mailbox_id in self.store.mailboxes:
            return self.store.mailboxes[user.mailbox_id]
        mtype = mailbox_type or (
            MailboxType.USER if user.origin == Origin.CLOUD_ONLY else MailboxType.REMOTE
        )
        return self.create_mailbox(user.display_name, user.sam, mtype, user_id=user.id)

    def set_mailbox_forwarding(self, mailbox_id: str, smtp: str | None) -> Mailbox:
        mb = self.get_mailbox(mailbox_id)
        mb.forwarding = smtp or None
        self._job("forwarding", mb.primary_smtp, smtp or "cleared")
        return mb

    def set_litigation_hold(self, mailbox_id: str, hold: bool) -> Mailbox:
        mb = self.get_mailbox(mailbox_id)
        mb.litigation_hold = hold
        self._job("litigation_hold", mb.primary_smtp, str(hold))
        return mb

    def set_auto_reply(self, mailbox_id: str, enabled: bool) -> Mailbox:
        mb = self.get_mailbox(mailbox_id)
        mb.auto_reply = enabled
        self._job("auto_reply", mb.primary_smtp, str(enabled))
        return mb

    def set_archive(self, mailbox_id: str, enabled: bool) -> Mailbox:
        mb = self.get_mailbox(mailbox_id)
        mb.archive = enabled
        self._job("archive", mb.primary_smtp, str(enabled))
        return mb

    def set_hidden(self, mailbox_id: str, hidden: bool) -> Mailbox:
        mb = self.get_mailbox(mailbox_id)
        mb.hidden = hidden
        self._job("hidden_from_addresslist", mb.primary_smtp, str(hidden))
        return mb

    def list_permissions(self, mailbox_id: str | None = None) -> list[MailboxPermission]:
        perms = list(self.store.permissions.values())
        if mailbox_id:
            perms = [p for p in perms if p.mailbox_id == mailbox_id]
        return perms

    def grant_permission(
        self,
        mailbox_id: str,
        trustee: str,
        rights: MailboxRight,
        automapping: bool = True,
        calendar_level: str | None = None,
    ) -> MailboxPermission:
        mb = self.get_mailbox(mailbox_id)
        trustee_name = trustee
        for user in self.store.users.values():
            if user.upn == trustee or user.sam == trustee or user.display_name == trustee:
                trustee = user.upn
                trustee_name = user.display_name
                break
        pid = _id("p")
        perm = MailboxPermission(
            id=pid,
            mailbox_id=mb.id,
            trustee=trustee,
            trustee_name=trustee_name,
            rights=rights,
            automapping=automapping if rights == MailboxRight.FULL_ACCESS else False,
            calendar_level=calendar_level if rights == MailboxRight.CALENDAR else None,
        )
        self.store.permissions[pid] = perm
        self._job("grant_permission", mb.primary_smtp, f"{rights.value} -> {trustee}")
        return perm

    def revoke_permission(self, permission_id: str) -> None:
        perm = self.store.permissions.pop(permission_id, None)
        if not perm:
            raise HatuiError(f"permission not found: {permission_id}")
        mb = self.store.mailboxes.get(perm.mailbox_id)
        self._job("revoke_permission", mb.primary_smtp if mb else permission_id, f"{perm.rights.value} {perm.trustee}")

    def list_mail_flow(self) -> list[MailFlowConnector]:
        return list(self.store.mail_flow.values())

    def list_cloud_users(self, query: str = "") -> list[User]:
        users = [
            u
            for u in self.list_users(query)
            if u.origin in {Origin.SYNCED, Origin.CLOUD_ONLY} and not u.guest
        ]
        return users

    def list_guests(self, query: str = "") -> list[User]:
        return [u for u in self.list_users(query) if u.guest]

    def list_licenses(self) -> list[LicenseSku]:
        return list(self.store.licenses.values())

    def assign_license(self, user_id: str, sku: str) -> User:
        user = self._user(user_id)
        lic = next((x for x in self.store.licenses.values() if x.sku == sku or x.name == sku), None)
        if not lic:
            raise HatuiError(f"SKU not found: {sku}")
        if lic.sku in user.licenses:
            return user
        if lic.available <= 0:
            raise HatuiError(f"no seats left for {lic.name}")
        user.licenses.append(lic.sku)
        lic.consumed += 1
        lic.available -= 1
        if user.mailbox_id:
            self.store.mailboxes[user.mailbox_id].licensed = True
        self._job("assign_license", user.upn, lic.sku)
        return user

    def remove_license(self, user_id: str, sku: str) -> User:
        user = self._user(user_id)
        lic = next((x for x in self.store.licenses.values() if x.sku == sku or x.name == sku), None)
        if not lic:
            raise HatuiError(f"SKU not found: {sku}")
        if lic.sku in user.licenses:
            user.licenses.remove(lic.sku)
            lic.consumed = max(0, lic.consumed - 1)
            lic.available += 1
        if user.mailbox_id and not user.licenses:
            self.store.mailboxes[user.mailbox_id].licensed = False
        self._job("remove_license", user.upn, lic.sku)
        return user

    def list_roles(self) -> list[DirectoryRole]:
        return list(self.store.roles.values())

    def list_soft_deleted(self) -> list[SoftDeleted]:
        return list(self.store.soft_deleted.values())

    def restore_deleted(self, object_id: str) -> User:
        item = self.store.soft_deleted.pop(object_id, None)
        if not item:
            raise HatuiError(f"deleted object not found: {object_id}")
        user = self.create_user(
            display_name=item.display_name,
            upn=item.upn,
            sam=item.upn.split("@")[0].replace(".", "")[:20],
            origin=Origin.SYNCED.value,
        )
        self._job("restore", item.upn, "restored from recycle bin")
        return user

    def sync_status(self) -> SyncStatus:
        return self.store.sync

    def run_delta_sync(self) -> SyncStatus:
        self.store.sync.cycle = "delta"
        self.store.sync.in_progress = False
        self.store.sync.last_delta = _now()
        self.store.sync.exported = len([u for u in self.store.users.values() if u.origin == Origin.SYNCED])
        self.store.sync.errors = sum(1 for u in self.store.users.values() if u.sync_error)
        self.store.sync.cycle = "idle"
        self._job("delta_sync", self.store.sync.server, f"exported={self.store.sync.exported}")
        return self.store.sync

    def run_full_sync(self) -> SyncStatus:
        self.store.sync.last_full = _now()
        self.store.sync.last_delta = _now()
        self.store.sync.exported = len([u for u in self.store.users.values() if u.origin == Origin.SYNCED])
        self.store.sync.cycle = "idle"
        self._job("full_sync", self.store.sync.server, "full import/export complete")
        return self.store.sync

    def forest_health(self) -> ForestHealth:
        health = forest_from(self.store)
        health.mode = "MOCK"
        return health

    def connector_status(self) -> list[ConnectorStatus]:
        return list(self.store.connectors)

    def list_jobs(self) -> list[Job]:
        return list(self.store.jobs)

    def list_audit(self) -> list[AuditEvent]:
        return list(self.store.audit)
