from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MailboxType(str, Enum):
    USER = "UserMailbox"
    REMOTE = "RemoteMailbox"
    SHARED = "SharedMailbox"
    ROOM = "RoomMailbox"
    EQUIPMENT = "EquipmentMailbox"


class MailboxRight(str, Enum):
    FULL_ACCESS = "FullAccess"
    SEND_AS = "SendAs"
    SEND_ON_BEHALF = "SendOnBehalf"
    CALENDAR = "Calendar"


class Mailbox(BaseModel):
    id: str
    alias: str
    primary_smtp: str
    display_name: str
    mailbox_type: MailboxType = MailboxType.REMOTE
    user_id: str | None = None
    quota_gb: float = 50.0
    used_gb: float = 0.0
    forwarding: str | None = None
    litigation_hold: bool = False
    archive: bool = False
    auto_reply: bool = False
    licensed: bool = True
    hidden: bool = False
    recipient_type: str = "UserMailbox"
    database: str = "EXO"
    created: datetime | None = None
    automapping_default: bool = True


class MailboxPermission(BaseModel):
    id: str
    mailbox_id: str
    trustee: str
    trustee_name: str
    rights: MailboxRight
    automapping: bool = True
    calendar_level: str | None = None


class MailFlowConnector(BaseModel):
    id: str
    name: str
    direction: str
    status: str = "enabled"
    host: str = ""
    smart_host: str | None = None
