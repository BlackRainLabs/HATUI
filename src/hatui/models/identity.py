from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Origin(str, Enum):
    ONPREM = "on-prem"
    SYNCED = "synced"
    CLOUD_ONLY = "cloud-only"


class User(BaseModel):
    id: str
    sam: str
    upn: str
    display_name: str
    given_name: str = ""
    surname: str = ""
    mail: str | None = None
    department: str = ""
    title: str = ""
    office: str = ""
    ou: str = ""
    enabled: bool = True
    locked: bool = False
    origin: Origin = Origin.SYNCED
    immutable_id: str | None = None
    last_sync: datetime | None = None
    must_change_password: bool = False
    last_logon: datetime | None = None
    manager_id: str | None = None
    company: str = "BlackRainLabs"
    employee_id: str = ""
    proxy_addresses: list[str] = Field(default_factory=list)
    licenses: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    mailbox_id: str | None = None
    guest: bool = False
    sync_error: str | None = None


class GroupType(str, Enum):
    SECURITY = "security"
    DISTRIBUTION = "distribution"
    MAIL_SECURITY = "mail-enabled-security"
    M365 = "m365"


class Group(BaseModel):
    id: str
    name: str
    sam: str
    mail: str | None = None
    group_type: GroupType = GroupType.SECURITY
    scope: Literal["Global", "Universal", "DomainLocal"] = "Global"
    ou: str = ""
    description: str = ""
    member_ids: list[str] = Field(default_factory=list)
    nested_group_ids: list[str] = Field(default_factory=list)
    origin: Origin = Origin.SYNCED
    privileged: bool = False


class Computer(BaseModel):
    id: str
    name: str
    sam: str
    os: str = "Windows 11"
    ou: str = ""
    enabled: bool = True
    last_logon: datetime | None = None
    origin: Origin = Origin.ONPREM
    managed: bool = False
    ip: str = ""
    spn: list[str] = Field(default_factory=list)


class Contact(BaseModel):
    id: str
    display_name: str
    mail: str
    company: str = ""
    ou: str = ""
    origin: Origin = Origin.ONPREM


class ServiceAccount(BaseModel):
    id: str
    sam: str
    display_name: str
    kind: Literal["user", "gMSA", "managed"] = "user"
    ou: str = ""
    spn: list[str] = Field(default_factory=list)
    enabled: bool = True
    description: str = ""
