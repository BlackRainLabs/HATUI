from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.events import Click
from textual.widgets import Static, Tree

from hatui.models import HealthState
from hatui.ui.catalog import NAV
from hatui.ui.messages import Navigate

UTC = timezone.utc

_HEALTH_COLOR = {
    HealthState.HEALTHY: "#c5ccd4",
    HealthState.ONLINE: "#c5ccd4",
    HealthState.SYNCED: "#c5ccd4",
    HealthState.MOCK: "#c4a35a",
    HealthState.LIVE: "#c5ccd4",
    HealthState.DEGRADED: "#c4a35a",
    HealthState.PENDING: "#c4a35a",
    HealthState.ERROR: "#c44545",
    HealthState.DOWN: "#c44545",
}


def _pill(label: str, state: str, color: str) -> str:
    return f"{label}:[{color}]{state}[/]"


class OpsHeader(Horizontal):
    def compose(self) -> ComposeResult:
        yield Static("BRL", id="brand")
        yield Static("HATUI", id="product")
        yield Static("", id="org")
        yield Static("", id="health")
        yield Static("", id="clock")

    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        app = self.app
        cfg = getattr(app, "config", None)
        backend = getattr(app, "backend", None)
        org = getattr(cfg, "org_name", "BlackRainLabs") if cfg else "BlackRainLabs"
        domain = getattr(cfg, "domain", "blackrainlabs.corp") if cfg else "blackrainlabs.corp"
        tenant = getattr(cfg, "entra_tenant", "") if cfg else ""
        who = ""
        if cfg:
            who = getattr(cfg, "session_user", "") or getattr(cfg.ldap, "username", "") or getattr(cfg.graph, "username", "")
        identity = who or tenant
        self.query_one("#org", Static).update(f"{org}  ·  {domain}  ·  {identity}")
        if backend is None:
            return
        health = backend.forest_health()
        f_cls = _HEALTH_COLOR.get(health.forest_state, "dim")
        x_cls = _HEALTH_COLOR.get(health.exo_state, "dim")
        e_cls = _HEALTH_COLOR.get(health.entra_state, "dim")
        mode_cls = "#c4a35a" if health.mode == "MOCK" else "#c5ccd4"
        text = (
            f"{_pill('FOREST', health.forest_state.value, f_cls)}   "
            f"{_pill('EXO', health.exo_state.value, x_cls)}   "
            f"{_pill('ENTRA', health.entra_state.value, e_cls)}   "
            f"{_pill('MODE', health.mode, mode_cls)}"
        )
        self.query_one("#health", Static).update(text)
        now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%SZ")
        self.query_one("#clock", Static).update(now)


class OpsFooter(Static):
    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self, module: str = "") -> None:
        app = self.app
        backend = getattr(app, "backend", None)
        jobs = 0
        lights = "AD·SYNC·EXO"
        if backend is not None:
            jobs = len(backend.list_jobs())
            cons = backend.connector_status()
            bits = []
            for c in cons:
                mark = "●" if c.live else "○"
                bits.append(f"{mark}{c.kind[:2].upper()}")
            lights = " ".join(bits) if bits else lights
        mod = f"[{module}]  " if module else ""
        self.update(
            f"{mod}BRL  F1 help   / filter   a actions   n new   r reload   : jump   ^L login   q quit"
            f"     2×row=actions   JOBS:{jobs}   {lights}"
        )


class Sidebar(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Tree("BLACKRAIN", id="nav")

    def on_mount(self) -> None:
        tree = self.query_one("#nav", Tree)
        tree.root.expand()
        tree.show_root = False
        for section, items in NAV:
            node = tree.root.add(section, data=None, expand=section in {"IDENTITY", "EXCHANGE", "DASHBOARD"})
            if section == "DASHBOARD":
                node.data = "dashboard"
                continue
            for module_id, label in items:
                node.add_leaf(label, data=module_id)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if isinstance(data, str) and data:
            self.post_message(Navigate(data))

    def on_click(self, event: Click) -> None:
        if event.chain < 2:
            return
        tree = self.query_one("#nav", Tree)
        node = tree.cursor_node
        if node is None:
            return
        if node.allow_expand and node.children:
            if node.is_expanded:
                node.collapse()
            else:
                node.expand()
        data = node.data
        if isinstance(data, str) and data:
            self.post_message(Navigate(data))
            event.stop()


class Inspector(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("INSPECTOR", id="inspector-title")
        yield Static("Select an object.", id="inspector-body")

    def show(self, fields: list[tuple[str, str]], title: str = "INSPECTOR") -> None:
        self.query_one("#inspector-title", Static).update(title)
        if not fields:
            self.query_one("#inspector-body", Static).update("Select an object.")
            return
        lines = []
        for key, val in fields:
            cls = "val"
            upper = str(val).upper()
            if upper in {"TRUE", "Y", "HEALTHY", "ONLINE", "SYNCED", "LIVE", "OK"}:
                cls = "ok"
            elif upper in {"FALSE", "N", "LOCKED", "DISABLED", "DEGRADED", "MOCK"}:
                cls = "warn"
            elif upper in {"CRITICAL", "DOWN", "ERROR"} or "conflict" in str(val).lower():
                cls = "crit"
            color = {"ok": "#c5ccd4", "warn": "#c4a35a", "crit": "#c44545", "val": "#e4e6e9"}.get(cls, "#e4e6e9")
            lines.append(f"[dim]{key}[/]\n[{color}]{val}[/]")
        self.query_one("#inspector-body", Static).update("\n\n".join(lines))
