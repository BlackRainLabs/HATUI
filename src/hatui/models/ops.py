from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from hatui.models.directory import HealthState


class Job(BaseModel):
    id: str
    action: str
    target: str
    status: Literal["queued", "running", "ok", "failed"] = "ok"
    created: datetime
    message: str = ""


class AuditEvent(BaseModel):
    id: str
    at: datetime
    actor: str = "BRL-HATUI"
    action: str
    target: str
    detail: str = ""


class Alert(BaseModel):
    id: str
    severity: Literal["crit", "warn", "ok"]
    source: str
    message: str


class ForestHealth(BaseModel):
    forest: str
    domain: str
    forest_state: HealthState = HealthState.HEALTHY
    exo_state: HealthState = HealthState.ONLINE
    entra_state: HealthState = HealthState.SYNCED
    mode: str = "MOCK"
    dc_online: int = 0
    dc_total: int = 0
    users: int = 0
    mailboxes: int = 0
    licenses_consumed: int = 0
    licenses_total: int = 0
    sync: str = "idle"
    alerts: list[Alert] = []
