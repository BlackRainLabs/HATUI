from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LicenseSku(BaseModel):
    sku: str
    name: str
    total: int
    consumed: int
    available: int


class DirectoryRole(BaseModel):
    id: str
    name: str
    member_ids: list[str] = Field(default_factory=list)


class SoftDeleted(BaseModel):
    id: str
    display_name: str
    upn: str
    kind: str = "user"
    deleted: datetime | None = None
    days_remaining: int = 30


class MatchKind(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    NONE = "none"


class SyncStatus(BaseModel):
    last_delta: datetime | None = None
    last_full: datetime | None = None
    in_progress: bool = False
    cycle: str = "idle"
    exported: int = 0
    errors: int = 0
    staging: bool = False
    server: str = "BRL-AAD01.blackrainlabs.corp"
    version: str = "2.4.18.0"


class ConnectorStatus(BaseModel):
    name: str
    kind: str
    live: bool
    detail: str = ""
    health: str = "MOCK"
