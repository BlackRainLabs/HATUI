from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Static

from hatui.models import ForestHealth, GroupType, MailboxType, Origin


def _bar(used: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "─" * width
    fill = max(0, min(width, round(width * used / total)))
    return "█" * fill + "░" * (width - fill)


class Dashboard(VerticalScroll):
    def __init__(self, backend: object) -> None:
        super().__init__()
        self.backend = backend

    def compose(self) -> ComposeResult:
        yield Static("DASHBOARD", id="view-title")
        health: ForestHealth = self.backend.forest_health()  # type: ignore[attr-defined]
        users = self.backend.list_users()  # type: ignore[attr-defined]
        mailboxes = self.backend.list_mailboxes()  # type: ignore[attr-defined]
        groups = self.backend.list_groups()  # type: ignore[attr-defined]
        sync = self.backend.sync_status()  # type: ignore[attr-defined]
        jobs = self.backend.list_jobs()[:6]  # type: ignore[attr-defined]
        alerts = health.alerts

        synced = sum(1 for u in users if u.origin == Origin.SYNCED)
        cloud = sum(1 for u in users if u.origin == Origin.CLOUD_ONLY)
        onprem = sum(1 for u in users if u.origin == Origin.ONPREM)
        remote = sum(1 for m in mailboxes if m.mailbox_type == MailboxType.REMOTE)
        shared = sum(1 for m in mailboxes if m.mailbox_type == MailboxType.SHARED)
        dls = sum(1 for g in groups if g.group_type != GroupType.SECURITY)

        with Grid(classes="dash-grid"):
            with Vertical(classes="panel"):
                yield Static("FOREST", classes="panel-title")
                yield Static(
                    f"domain     {health.domain}\n"
                    f"DCs        {health.dc_online}/{health.dc_total} online\n"
                    f"users      {health.users}  (sync {synced} / cloud {cloud} / on-prem {onprem})\n"
                    f"mailboxes  {health.mailboxes}  (remote {remote} / shared {shared})\n"
                    f"groups     {len(groups)}  mail-enabled {dls}\n"
                    f"mode       {health.mode}"
                )
            with Vertical(classes="panel"):
                yield Static("ENTRA / EXO", classes="panel-title")
                yield Static(
                    f"EXO        {health.exo_state.value}\n"
                    f"Entra      {health.entra_state.value}\n"
                    f"licenses   {health.licenses_consumed}/{health.licenses_total}\n"
                    f"{_bar(health.licenses_consumed, health.licenses_total)}\n"
                    f"sync host  {sync.server}\n"
                    f"last delta {_fmt(sync.last_delta)}\n"
                    f"errors     {sync.errors}"
                )
            with Vertical(classes="panel"):
                yield Static("ALERTS", classes="panel-title")
                lines = []
                for alert in alerts:
                    color = {"crit": "#c44545", "warn": "#c4a35a", "ok": "#c5ccd4"}[alert.severity]
                    lines.append(f"[{color}]{alert.severity.upper():5}[/] {alert.source}: {alert.message}")
                yield Static("\n".join(lines) or "none")
            with Vertical(classes="panel"):
                yield Static("RECENT JOBS", classes="panel-title")
                jlines = [f"{j.status:7} {j.action:16} {j.target}" for j in jobs] or ["—"]
                yield Static("\n".join(jlines))


def _fmt(value) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")


class SyncView(Vertical):
    def __init__(self, backend: object) -> None:
        super().__init__()
        self.backend = backend

    def compose(self) -> ComposeResult:
        yield Static("AAD CONNECT", id="view-title")
        sync = self.backend.sync_status()  # type: ignore[attr-defined]
        yield Static(
            f"server       {sync.server}\n"
            f"version      {sync.version}\n"
            f"cycle        {sync.cycle}\n"
            f"in progress  {sync.in_progress}\n"
            f"last delta   {_fmt(sync.last_delta)}\n"
            f"last full    {_fmt(sync.last_full)}\n"
            f"exported     {sync.exported}\n"
            f"errors       {sync.errors}\n"
            f"staging      {sync.staging}\n",
            id="sync-body",
        )
        with Horizontal(id="sync-buttons"):
            yield Button("Delta sync", id="delta", classes="primary")
            yield Button("Full sync", id="full")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delta":
            self.backend.run_delta_sync()  # type: ignore[attr-defined]
            self.app.notify("Delta sync complete")
        elif event.button.id == "full":
            self.backend.run_full_sync()  # type: ignore[attr-defined]
            self.app.notify("Full sync complete")
        sync = self.backend.sync_status()  # type: ignore[attr-defined]
        self.query_one("#sync-body", Static).update(
            f"server       {sync.server}\n"
            f"version      {sync.version}\n"
            f"cycle        {sync.cycle}\n"
            f"in progress  {sync.in_progress}\n"
            f"last delta   {_fmt(sync.last_delta)}\n"
            f"last full    {_fmt(sync.last_full)}\n"
            f"exported     {sync.exported}\n"
            f"errors       {sync.errors}\n"
            f"staging      {sync.staging}\n"
        )
        header = self.app.query_one("OpsHeader")
        header.refresh_status()  # type: ignore[attr-defined]


class SettingsView(VerticalScroll):
    def __init__(self, config: object) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield Static("SETTINGS", id="view-title")
        cfg = self.config
        yield Static(
            f"mode           {cfg.mode}\n"
            f"org            {cfg.org_name}\n"
            f"domain         {cfg.domain}\n"
            f"entra tenant   {cfg.entra_tenant}\n"
            f"exchange org   {cfg.exchange_org}\n"
            f"ldap enabled   {cfg.ldap.enabled}\n"
            f"ldap auth      {cfg.ldap.auth}\n"
            f"ldap server    {cfg.ldap.server or '—'}\n"
            f"ldap user      {cfg.ldap.username or '—'}\n"
            f"ldap bind      {cfg.ldap.bind_dn or '—'}\n"
            f"ldap base      {cfg.ldap.base_dn or '—'}\n"
            f"graph enabled  {cfg.graph.enabled}\n"
            f"graph auth     {cfg.graph.auth}\n"
            f"graph tenant   {cfg.graph.tenant_id or '—'}\n"
            f"graph client   {cfg.graph.client_id or '—'}\n"
            f"graph user     {cfg.graph.username or '—'}\n"
            f"session        {getattr(cfg, 'session_user', '') or '—'}\n"
            f"secrets        HATUI_USERNAME / HATUI_PASSWORD\n"
            f"               HATUI_LDAP_PASSWORD / HATUI_GRAPH_PASSWORD / HATUI_GRAPH_CLIENT_SECRET\n",
            classes="panel",
        )
