from __future__ import annotations

from datetime import datetime, timezone

import httpx

from hatui.config import GraphConfig
from hatui.models import (
    DirectoryRole,
    LicenseSku,
    Mailbox,
    MailboxPermission,
    MailboxRight,
    MailboxType,
    MailFlowConnector,
    Origin,
    SoftDeleted,
    User,
)
from hatui.services.auth import graph_token_form, graph_token_url
from hatui.services.protocol import HatuiError, NotConfiguredError

GRAPH = "https://graph.microsoft.com/v1.0"


def _require(cfg: GraphConfig) -> None:
    if not (cfg.enabled and cfg.tenant_id and cfg.client_id):
        raise NotConfiguredError("Graph connector is not configured (tenant_id/client_id).")
    if cfg.auth == "login":
        if not cfg.username:
            raise NotConfiguredError("Graph login requires a username (UPN).")
        return
    if not cfg.client_secret:
        raise NotConfiguredError("HATUI_GRAPH_CLIENT_SECRET is not set.")


class GraphBackend:
    """Entra + Exchange Online via Microsoft Graph (login or client credentials)."""

    def __init__(self, cfg: GraphConfig) -> None:
        _require(cfg)
        self.cfg = cfg
        self._token: str | None = None

    def authenticate(self) -> str:
        self._access_token()
        return self.cfg.username or self.cfg.client_id

    def _access_token(self) -> str:
        if self._token:
            return self._token
        url = graph_token_url(self.cfg)
        data = graph_token_form(self.cfg)
        resp = httpx.post(url, data=data, timeout=30.0)
        if resp.status_code >= 400:
            raise HatuiError(f"Graph token failed: {resp.status_code} {resp.text[:240]}")
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token()}"}

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = httpx.get(f"{GRAPH}{path}", headers=self._headers(), params=params, timeout=30.0)
        if resp.status_code >= 400:
            raise HatuiError(f"Graph GET {path} failed: {resp.status_code} {resp.text[:240]}")
        return resp.json()

    def _post(self, path: str, json: dict) -> dict:
        resp = httpx.post(f"{GRAPH}{path}", headers=self._headers(), json=json, timeout=30.0)
        if resp.status_code >= 400:
            raise HatuiError(f"Graph POST {path} failed: {resp.status_code} {resp.text[:240]}")
        return resp.json() if resp.content else {}

    def _patch(self, path: str, json: dict) -> dict:
        resp = httpx.patch(f"{GRAPH}{path}", headers=self._headers(), json=json, timeout=30.0)
        if resp.status_code >= 400:
            raise HatuiError(f"Graph PATCH {path} failed: {resp.status_code} {resp.text[:240]}")
        return resp.json() if resp.content else {}

    def _user_from(self, raw: dict) -> User:
        upn = raw.get("userPrincipalName") or ""
        origin = Origin.CLOUD_ONLY
        if raw.get("onPremisesSyncEnabled"):
            origin = Origin.SYNCED
        return User(
            id=raw.get("id") or upn,
            sam=(upn.split("@")[0] if upn else raw.get("id", "")[:20]),
            upn=upn,
            display_name=raw.get("displayName") or upn,
            mail=raw.get("mail"),
            department=raw.get("department") or "",
            title=raw.get("jobTitle") or "",
            origin=origin,
            guest=raw.get("userType") == "Guest",
            enabled=raw.get("accountEnabled", True),
            immutable_id=raw.get("onPremisesImmutableId"),
        )

    def list_cloud_users(self, query: str = "") -> list[User]:
        data = self._get("/users", params={"$top": "999", "$select": "id,displayName,userPrincipalName,mail,department,jobTitle,accountEnabled,userType,onPremisesSyncEnabled,onPremisesImmutableId"})
        users = [self._user_from(x) for x in data.get("value", [])]
        if query:
            q = query.lower()
            users = [u for u in users if q in f"{u.display_name} {u.upn} {u.mail}".lower()]
        return [u for u in users if not u.guest]

    def list_guests(self, query: str = "") -> list[User]:
        data = self._get("/users", params={"$filter": "userType eq 'Guest'", "$top": "999"})
        users = [self._user_from(x) for x in data.get("value", [])]
        if query:
            q = query.lower()
            users = [u for u in users if q in f"{u.display_name} {u.upn}".lower()]
        return users

    def list_licenses(self) -> list[LicenseSku]:
        data = self._get("/subscribedSkus")
        out = []
        for sku in data.get("value", []):
            consumed = int(sku.get("consumedUnits") or 0)
            enabled = (sku.get("prepaidUnits") or {}).get("enabled") or 0
            out.append(
                LicenseSku(
                    sku=sku.get("skuPartNumber") or sku.get("skuId") or "",
                    name=sku.get("skuPartNumber") or "SKU",
                    total=int(enabled),
                    consumed=consumed,
                    available=max(0, int(enabled) - consumed),
                )
            )
        return out

    def assign_license(self, user_id: str, sku: str) -> User:
        skus = self.list_licenses()
        match = next((s for s in skus if s.sku == sku), None)
        if not match:
            raise HatuiError(f"SKU not found: {sku}")
        subscribed = self._get("/subscribedSkus")
        sku_id = next(s["skuId"] for s in subscribed.get("value", []) if s.get("skuPartNumber") == sku)
        self._post(f"/users/{user_id}/assignLicense", {"addLicenses": [{"skuId": sku_id}], "removeLicenses": []})
        users = self.list_cloud_users()
        return next(u for u in users if u.id == user_id)

    def remove_license(self, user_id: str, sku: str) -> User:
        subscribed = self._get("/subscribedSkus")
        sku_id = next(s["skuId"] for s in subscribed.get("value", []) if s.get("skuPartNumber") == sku)
        self._post(f"/users/{user_id}/assignLicense", {"addLicenses": [], "removeLicenses": [sku_id]})
        users = self.list_cloud_users()
        return next(u for u in users if u.id == user_id)

    def list_roles(self) -> list[DirectoryRole]:
        data = self._get("/directoryRoles")
        roles = []
        for raw in data.get("value", []):
            members = self._get(f"/directoryRoles/{raw['id']}/members")
            roles.append(
                DirectoryRole(
                    id=raw["id"],
                    name=raw.get("displayName") or "",
                    member_ids=[m.get("id") for m in members.get("value", []) if m.get("id")],
                )
            )
        return roles

    def list_soft_deleted(self) -> list[SoftDeleted]:
        data = self._get("/directory/deletedItems/microsoft.graph.user")
        out = []
        for raw in data.get("value", []):
            deleted = raw.get("deletedDateTime")
            when = datetime.fromisoformat(deleted.replace("Z", "+00:00")) if deleted else datetime.now(tz=timezone.utc)
            out.append(
                SoftDeleted(
                    id=raw.get("id") or "",
                    display_name=raw.get("displayName") or "",
                    upn=raw.get("userPrincipalName") or "",
                    deleted=when,
                )
            )
        return out

    def restore_deleted(self, object_id: str) -> User:
        raw = self._post(f"/directory/deletedItems/{object_id}/restore", {})
        return self._user_from(raw)

    def list_mailboxes(self, query: str = "") -> list[Mailbox]:
        users = self.list_cloud_users(query)
        boxes = []
        for user in users:
            if not user.mail:
                continue
            boxes.append(
                Mailbox(
                    id=user.id,
                    alias=user.sam,
                    primary_smtp=user.mail,
                    display_name=user.display_name,
                    mailbox_type=MailboxType.USER if user.origin == Origin.CLOUD_ONLY else MailboxType.REMOTE,
                    user_id=user.id,
                    recipient_type="UserMailbox",
                    licensed=True,
                )
            )
        return boxes

    def get_mailbox(self, mailbox_id: str) -> Mailbox:
        for mb in self.list_mailboxes():
            if mb.id == mailbox_id:
                return mb
        raise HatuiError(f"mailbox not found: {mailbox_id}")

    def create_mailbox(
        self,
        display_name: str,
        alias: str,
        mailbox_type: MailboxType,
        user_id: str | None = None,
    ) -> Mailbox:
        raise HatuiError(
            "Creating EXO mailboxes via Graph requires a licensed user or shared-mailbox Graph API; "
            "enable the mailbox on an existing Entra user or use mock mode."
        )

    def enable_mailbox(self, user_id: str, mailbox_type: MailboxType | None = None) -> Mailbox:
        raise HatuiError("Enable-Mailbox in live mode is Graph license assignment + EXO provisioning; assign an E3/E5/EXO SKU first.")

    def set_mailbox_forwarding(self, mailbox_id: str, smtp: str | None) -> Mailbox:
        body = {
            "forwardingSmtpAddress": smtp,
            "forwardingAddress": None,
        }
        self._patch(f"/users/{mailbox_id}/mailboxSettings", {"automaticRepliesSetting": {}} if False else {})
        # Graph mailboxSettings uses forwardingSmtpAddress under mailboxSettings in some tenants.
        self._patch(f"/users/{mailbox_id}/mailboxSettings", {"forwardingSmtpAddress": smtp})
        return self.get_mailbox(mailbox_id)

    def set_litigation_hold(self, mailbox_id: str, hold: bool) -> Mailbox:
        raise HatuiError("Litigation hold is not exposed on Microsoft Graph v1 mailboxSettings.")

    def set_auto_reply(self, mailbox_id: str, enabled: bool) -> Mailbox:
        self._patch(
            f"/users/{mailbox_id}/mailboxSettings",
            {"automaticRepliesSetting": {"status": "alwaysEnabled" if enabled else "disabled"}},
        )
        mb = self.get_mailbox(mailbox_id)
        mb.auto_reply = enabled
        return mb

    def set_archive(self, mailbox_id: str, enabled: bool) -> Mailbox:
        raise HatuiError("Archive mailbox enablement is not on Graph v1; use mock or EXO admin API.")

    def set_hidden(self, mailbox_id: str, hidden: bool) -> Mailbox:
        raise HatuiError("HiddenFromAddressListsEnabled is not on Graph v1 mailboxSettings.")

    def list_permissions(self, mailbox_id: str | None = None) -> list[MailboxPermission]:
        if not mailbox_id:
            return []
        try:
            data = self._get(f"/users/{mailbox_id}/mailFolders/inbox/messageRules")
        except HatuiError:
            return []
        # Folder-level permissions:
        try:
            data = self._get(f"/users/{mailbox_id}/mailFolders/inbox/permissions")
        except HatuiError:
            return []
        out = []
        for raw in data.get("value", []):
            out.append(
                MailboxPermission(
                    id=raw.get("id") or "",
                    mailbox_id=mailbox_id,
                    trustee=(raw.get("emailAddress") or {}).get("address") or "",
                    trustee_name=(raw.get("emailAddress") or {}).get("name") or "",
                    rights=MailboxRight.FULL_ACCESS,
                    automapping=True,
                )
            )
        return out

    def grant_permission(
        self,
        mailbox_id: str,
        trustee: str,
        rights: MailboxRight,
        automapping: bool = True,
        calendar_level: str | None = None,
    ) -> MailboxPermission:
        raise HatuiError(
            f"Live grant of {rights.value} requires Exchange.ManageAsApp / mailbox folder permissions; "
            "configure Graph app roles or use mock mode."
        )

    def revoke_permission(self, permission_id: str) -> None:
        raise HatuiError("Live revoke requires Graph folder permission delete; not configured.")

    def list_mail_flow(self) -> list[MailFlowConnector]:
        return []
