from __future__ import annotations

from typing import Any

from hatui.models import MailboxRight, MailboxType, Origin, User
from hatui.services.protocol import HatuiError


def resolve_user(backend: Any, token: str) -> User:
    for user in backend.list_users():
        if token in {user.id, user.upn, user.sam, user.display_name}:
            return user
    raise HatuiError(f"user not found: {token}")


def resolve_mailbox_id(backend: Any, token: str) -> str:
    for mb in backend.list_mailboxes():
        if token in {mb.id, mb.alias, mb.primary_smtp, mb.display_name}:
            return mb.id
    raise HatuiError(f"mailbox not found: {token}")


def _temp_password(user: User) -> str:
    return f"Tmp-{user.sam[:6]}-{user.employee_id[-4:] or '4821'}!"


def dispatch(backend: Any, module_id: str, action_id: str, obj: Any, values: dict[str, str]) -> str:
    if action_id == "new" and module_id in {"users", "cloud_users"}:
        user = backend.create_user(
            given_name=values.get("given_name", ""),
            surname=values.get("surname", ""),
            department=values.get("department", ""),
            title=values.get("title", ""),
            origin=values.get("origin") or Origin.SYNCED.value,
        )
        return f"created {user.upn}"

    if action_id == "new" and module_id == "groups":
        group = backend.create_group(
            name=values.get("name") or "New Group",
            sam=values.get("sam") or "",
            group_type=values.get("group_type") or "security",
            mail=values.get("mail") or None,
        )
        return f"created group {group.name}"

    if action_id == "new" and module_id == "ous":
        ou = backend.create_ou(values.get("name") or "NewOU", values.get("parent_id") or None, values.get("description") or "")
        return f"created {ou.dn}"

    if action_id == "new" and module_id in {"mailboxes", "resources"}:
        mb = backend.create_mailbox(
            values.get("display_name") or values.get("alias") or "mailbox",
            values.get("alias") or "alias",
            MailboxType(values.get("mailbox_type") or "SharedMailbox"),
        )
        return f"created {mb.primary_smtp} ({mb.mailbox_type.value})"

    if action_id == "enable":
        if hasattr(obj, "os"):
            backend.set_computer_enabled(obj.id, True)
            return f"enabled {obj.name}"
        if module_id == "gpos":
            backend.set_gpo_enabled(obj.id, True)
            return f"linked {obj.name}"
        backend.set_user_enabled(obj.id, True)
        return f"enabled {obj.upn}"

    if action_id == "disable":
        if hasattr(obj, "os"):
            backend.set_computer_enabled(obj.id, False)
            return f"disabled {obj.name}"
        if module_id == "gpos":
            backend.set_gpo_enabled(obj.id, False)
            return f"unlinked {obj.name}"
        backend.set_user_enabled(obj.id, False)
        return f"disabled {obj.upn}"

    if action_id == "unlock":
        backend.unlock_user(obj.id)
        return f"unlocked {obj.upn}"

    if action_id == "reset_password":
        temp = _temp_password(obj)
        backend.reset_password(obj.id, temp, True)
        return f"temp password for {obj.upn}: {temp}"

    if action_id == "enable_mailbox":
        mtype = MailboxType(values.get("mailbox_type") or "RemoteMailbox")
        mb = backend.enable_mailbox(obj.id, mtype)
        return f"mailbox {mb.primary_smtp} ({mb.mailbox_type.value})"

    if action_id == "assign_license":
        if module_id == "licenses":
            user = resolve_user(backend, values.get("user_id") or "")
            sku = obj.sku
        else:
            user = obj
            sku = values.get("sku") or "E3"
            sku_map = {"E3": "SPE_E3", "E5": "SPE_E5", "EXO": "EXCHANGESTANDARD", "P2": "AAD_PREMIUM_P2"}
            sku = sku_map.get(sku.upper(), sku)
        backend.assign_license(user.id, sku)
        return f"assigned {sku} to {user.upn}"

    if action_id == "remove_license":
        user = resolve_user(backend, values.get("user_id") or "")
        backend.remove_license(user.id, obj.sku)
        return f"removed {obj.sku} from {user.upn}"

    if action_id == "move_user":
        backend.move_user(obj.id, values.get("ou_id") or "ou-users")
        return f"moved {obj.upn}"

    if action_id == "add_to_group":
        backend.add_group_member(values.get("group_id") or "", obj.id)
        return f"added {obj.upn} to {values.get('group_id')}"

    if action_id == "add_member":
        user = resolve_user(backend, values.get("member_id") or "")
        backend.add_group_member(obj.id, user.id)
        return f"added {user.upn} to {obj.name}"

    if action_id == "remove_member":
        user = resolve_user(backend, values.get("member_id") or "")
        backend.remove_group_member(obj.id, user.id)
        return f"removed {user.upn} from {obj.name}"

    if action_id == "forward":
        smtp = (values.get("smtp") or "").strip() or None
        backend.set_mailbox_forwarding(obj.id, smtp)
        return f"forwarding {obj.alias} -> {smtp or 'cleared'}"

    if action_id == "hold_on":
        backend.set_litigation_hold(obj.id, True)
        return f"hold on {obj.alias}"
    if action_id == "hold_off":
        backend.set_litigation_hold(obj.id, False)
        return f"hold off {obj.alias}"
    if action_id == "archive_on":
        backend.set_archive(obj.id, True)
        return f"archive on {obj.alias}"
    if action_id == "archive_off":
        backend.set_archive(obj.id, False)
        return f"archive off {obj.alias}"
    if action_id == "autoreply_on":
        backend.set_auto_reply(obj.id, True)
        return f"auto-reply on {obj.alias}"
    if action_id == "autoreply_off":
        backend.set_auto_reply(obj.id, False)
        return f"auto-reply off {obj.alias}"
    if action_id == "hide":
        backend.set_hidden(obj.id, True)
        return f"hidden {obj.alias}"
    if action_id == "unhide":
        backend.set_hidden(obj.id, False)
        return f"visible {obj.alias}"

    if action_id == "grant":
        mailbox_id = obj.id if hasattr(obj, "mailbox_type") else resolve_mailbox_id(backend, values.get("mailbox_id") or "")
        trustee = values.get("trustee") or ""
        rights = MailboxRight(values.get("rights") or "FullAccess")
        automap = (values.get("automapping") or "Y").lower() not in {"n", "no", "false", "0"}
        backend.grant_permission(mailbox_id, trustee, rights, automap, values.get("calendar_level") or None)
        return f"granted {rights.value} to {trustee}"

    if action_id == "revoke":
        backend.revoke_permission(obj.id)
        return "permission revoked"

    if action_id == "restore":
        user = backend.restore_deleted(obj.id)
        return f"restored {user.upn}"

    if action_id == "delta_sync":
        st = backend.run_delta_sync()
        return f"delta sync complete exported={st.exported} errors={st.errors}"

    if action_id == "full_sync":
        st = backend.run_full_sync()
        return f"full sync complete exported={st.exported}"

    raise HatuiError(f"unknown action {module_id}/{action_id}")
