from __future__ import annotations

from hatui.config import LdapConfig
from hatui.models import (
    Computer,
    Contact,
    DomainController,
    FsmoRole,
    GpoLink,
    Group,
    GroupType,
    OrgUnit,
    Origin,
    ReplicationPartner,
    ServiceAccount,
    Site,
    Trust,
    User,
)
from hatui.services.auth import ldap_bind_identity
from hatui.services.protocol import HatuiError, NotConfiguredError


def _require(cfg: LdapConfig) -> None:
    if not (cfg.enabled and cfg.server):
        raise NotConfiguredError("LDAP connector is not configured (server).")
    ldap_bind_identity(cfg)


class LdapDirectoryBackend:
    """On-prem AD via ldap3. Login binds as the operator; bind auth uses a service DN."""

    def __init__(self, cfg: LdapConfig) -> None:
        _require(cfg)
        self.cfg = cfg
        self._conn = None

    def authenticate(self) -> str:
        self._connect()
        return ldap_bind_identity(self.cfg)

    def _connect(self):
        if self._conn is not None and self._conn.bound:
            return self._conn
        try:
            from ldap3 import ALL, Connection, Server
        except ImportError as exc:
            raise NotConfiguredError("ldap3 is not installed") from exc
        identity = ldap_bind_identity(self.cfg)
        if not self.cfg.password:
            raise HatuiError("LDAP password is empty — sign in with Ctrl+L")
        server = Server(self.cfg.server, use_ssl=self.cfg.use_ssl, get_info=ALL)
        conn = Connection(
            server,
            user=identity,
            password=self.cfg.password,
            auto_bind=True,
        )
        if not conn.bound:
            raise HatuiError(f"LDAP bind failed for {identity}: {conn.result}")
        self._conn = conn
        return conn

    def _search(self, filt: str, attrs: list[str]) -> list[dict]:
        conn = self._connect()
        conn.search(self.cfg.base_dn, filt, attributes=attrs)
        rows = []
        for entry in conn.entries:
            rows.append({a: (str(entry[a]) if a in entry else "") for a in attrs})
            rows[-1]["dn"] = str(entry.entry_dn)
        return rows

    def list_users(self, query: str = "") -> list[User]:
        filt = "(&(objectCategory=person)(objectClass=user)(!(sAMAccountName=*$)))"
        if query:
            q = query.replace(")", "")
            filt = f"(&(objectCategory=person)(objectClass=user)(|(cn=*{q}*)(sAMAccountName=*{q}*)(userPrincipalName=*{q}*)))"
        rows = self._search(filt, ["sAMAccountName", "userPrincipalName", "displayName", "mail", "department", "title", "userAccountControl"])
        users: list[User] = []
        for i, row in enumerate(rows):
            uac = row.get("userAccountControl") or "512"
            try:
                uac_i = int(str(uac).split()[0])
            except ValueError:
                uac_i = 512
            users.append(
                User(
                    id=row.get("dn") or f"ldap-u-{i}",
                    sam=row.get("sAMAccountName") or "",
                    upn=row.get("userPrincipalName") or "",
                    display_name=row.get("displayName") or row.get("sAMAccountName") or "",
                    mail=row.get("mail") or None,
                    department=row.get("department") or "",
                    title=row.get("title") or "",
                    origin=Origin.ONPREM,
                    enabled=not bool(uac_i & 2),
                    locked=bool(uac_i & 16),
                )
            )
        return users

    def get_user(self, user_id: str) -> User:
        for user in self.list_users():
            if user.id == user_id or user.upn == user_id or user.sam == user_id:
                return user
        raise HatuiError(f"LDAP user not found: {user_id}")

    def create_user(self, **fields: object) -> User:
        raise HatuiError("LDAP create_user requires a dedicated bind with user-creation rights; use mock or Graph for this lab path.")

    def set_user_enabled(self, user_id: str, enabled: bool) -> User:
        user = self.get_user(user_id)
        conn = self._connect()
        from ldap3 import MODIFY_REPLACE

        uac = 512 if enabled else 514
        ok = conn.modify(user.id, {"userAccountControl": [(MODIFY_REPLACE, [uac])]})
        if not ok:
            raise HatuiError(str(conn.result))
        user.enabled = enabled
        return user

    def unlock_user(self, user_id: str) -> User:
        user = self.get_user(user_id)
        conn = self._connect()
        from ldap3 import MODIFY_REPLACE

        conn.modify(user.id, {"lockoutTime": [(MODIFY_REPLACE, [0])]})
        user.locked = False
        return user

    def reset_password(self, user_id: str, temp: str, must_change: bool = True) -> User:
        if not self.cfg.use_ssl:
            raise HatuiError("password reset requires LDAPS")
        user = self.get_user(user_id)
        conn = self._connect()
        quoted = f'"{temp}"'.encode("utf-16-le")
        from ldap3 import MODIFY_REPLACE

        changes = {"unicodePwd": [(MODIFY_REPLACE, [quoted])]}
        if must_change:
            changes["pwdLastSet"] = [(MODIFY_REPLACE, [0])]
        if not conn.modify(user.id, changes):
            raise HatuiError(str(conn.result))
        user.must_change_password = must_change
        return user

    def move_user(self, user_id: str, ou_id: str) -> User:
        raise HatuiError("LDAP move is not enabled in this connector yet")

    def list_groups(self, query: str = "") -> list[Group]:
        filt = "(objectClass=group)"
        rows = self._search(filt, ["sAMAccountName", "cn", "mail", "description"])
        out: list[Group] = []
        for i, row in enumerate(rows):
            name = row.get("cn") or row.get("sAMAccountName") or f"group-{i}"
            if query and query.lower() not in name.lower():
                continue
            out.append(
                Group(
                    id=row.get("dn") or f"ldap-g-{i}",
                    name=name,
                    sam=row.get("sAMAccountName") or name,
                    mail=row.get("mail") or None,
                    group_type=GroupType.SECURITY,
                    description=row.get("description") or "",
                    origin=Origin.ONPREM,
                )
            )
        return out

    def create_group(self, **fields: object) -> Group:
        raise HatuiError("LDAP create_group is not enabled in this connector yet")

    def set_group_members(self, group_id: str, member_ids: list[str]) -> Group:
        raise HatuiError("LDAP set_group_members is not enabled in this connector yet")

    def add_group_member(self, group_id: str, member_id: str) -> Group:
        raise HatuiError("LDAP add_group_member is not enabled in this connector yet")

    def remove_group_member(self, group_id: str, member_id: str) -> Group:
        raise HatuiError("LDAP remove_group_member is not enabled in this connector yet")

    def list_computers(self, query: str = "") -> list[Computer]:
        rows = self._search("(objectClass=computer)", ["cn", "operatingSystem", "sAMAccountName"])
        comps = []
        for i, row in enumerate(rows):
            name = row.get("cn") or f"pc-{i}"
            if query and query.lower() not in name.lower():
                continue
            comps.append(
                Computer(
                    id=row.get("dn") or f"ldap-c-{i}",
                    name=name,
                    sam=row.get("sAMAccountName") or f"{name}$",
                    os=row.get("operatingSystem") or "",
                    origin=Origin.ONPREM,
                )
            )
        return comps

    def set_computer_enabled(self, computer_id: str, enabled: bool) -> Computer:
        raise HatuiError("LDAP computer enable/disable is not enabled in this connector yet")

    def list_contacts(self, query: str = "") -> list[Contact]:
        return []

    def list_service_accounts(self, query: str = "") -> list[ServiceAccount]:
        return []

    def list_ous(self) -> list[OrgUnit]:
        rows = self._search("(objectClass=organizationalUnit)", ["ou", "description"])
        ous = []
        for i, row in enumerate(rows):
            ous.append(
                OrgUnit(
                    id=row.get("dn") or f"ldap-ou-{i}",
                    name=row.get("ou") or "",
                    dn=row.get("dn") or "",
                    description=row.get("description") or "",
                )
            )
        return ous

    def create_ou(self, name: str, parent_id: str | None, description: str = "") -> OrgUnit:
        raise HatuiError("LDAP create_ou is not enabled in this connector yet")

    def list_dcs(self) -> list[DomainController]:
        return []

    def list_fsmo(self) -> list[FsmoRole]:
        return []

    def list_sites(self) -> list[Site]:
        return []

    def list_gpos(self) -> list[GpoLink]:
        return []

    def set_gpo_enabled(self, gpo_id: str, enabled: bool) -> GpoLink:
        raise HatuiError("GPO link changes require a directory write path not enabled here")

    def list_replication(self) -> list[ReplicationPartner]:
        return []

    def list_trusts(self) -> list[Trust]:
        return []
