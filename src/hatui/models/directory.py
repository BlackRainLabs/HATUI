from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrgUnit(BaseModel):
    id: str
    name: str
    dn: str
    parent_id: str | None = None
    description: str = ""
    protected: bool = False


class DomainController(BaseModel):
    id: str
    name: str
    site: str
    ipv4: str
    os: str = "Windows Server 2022"
    gc: bool = True
    rodcs: bool = False
    online: bool = True
    fsmo: list[str] = Field(default_factory=list)


class FsmoRole(BaseModel):
    role: str
    holder: str
    scope: str


class Site(BaseModel):
    id: str
    name: str
    subnets: list[str] = Field(default_factory=list)
    location: str = ""
    dc_ids: list[str] = Field(default_factory=list)


class GpoLink(BaseModel):
    id: str
    name: str
    target_ou: str
    enabled: bool = True
    enforced: bool = False
    status: str = "applied"
    wmi_filter: str | None = None


class ReplicationPartner(BaseModel):
    source: str
    dest: str
    last_success: datetime | None = None
    fails: int = 0
    naming_context: str = ""


class Trust(BaseModel):
    id: str
    remote: str
    direction: str = "bidirectional"
    kind: str = "forest"
    transitive: bool = True
    healthy: bool = True


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    SYNCED = "SYNCED"
    PENDING = "PENDING"
    ERROR = "ERROR"
    ONLINE = "ONLINE"
    MOCK = "MOCK"
    LIVE = "LIVE"
