from __future__ import annotations

import argparse
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical
from textual.theme import Theme
from textual.widgets import Input

from hatui.config import HatuiConfig, load_config
from hatui.services.factory import create_backend
from hatui.services.protocol import HatuiError
from hatui.ui.browser import ObjectBrowser
from hatui.ui.catalog import CATALOG, JUMP_ALIASES, resolve_jump
from hatui.ui.chrome import Inspector, OpsFooter, OpsHeader, Sidebar
from hatui.ui.messages import ActivateObject, Navigate, SelectionChanged
from hatui.ui.modals import ActionMenu, ConfirmModal, FormModal, HelpScreen, JumpModal, LoginModal
from hatui.ui.screens import Dashboard, SettingsView, SyncView
from hatui.ui.actions import dispatch

BLACKRAIN = Theme(
    name="blackrain",
    primary="#c5ccd4",
    secondary="#8b939c",
    accent="#7f93a6",
    foreground="#e4e6e9",
    background="#070708",
    surface="#121316",
    panel="#16171a",
    success="#9aaba6",
    warning="#c4a35a",
    error="#c44545",
    dark=True,
    variables={
        "block-cursor-background": "#c5ccd4",
        "block-cursor-foreground": "#070708",
        "footer-key-foreground": "#c5ccd4",
        "button-color-foreground": "#070708",
        "input-selection-background": "#7f93a6 35%",
    },
)


class JumpProvider(Provider):
    async def search(self, query: str) -> Hits:
        q = query.lower().strip()
        seen: set[str] = set()
        for alias, module_id in JUMP_ALIASES.items():
            if module_id in seen:
                continue
            title = CATALOG[module_id].title if module_id in CATALOG else module_id
            hay = f"{module_id} {title} {alias}"
            if q and q not in hay.lower():
                continue
            seen.add(module_id)
            yield Hit(
                1.0 if q == module_id else 0.75,
                f"open {title}",
                lambda mid=module_id: self.app.switch_module(mid),  # type: ignore[attr-defined]
                help=f"Jump to {title}",
            )


class HatuiApp(App):
    TITLE = "HATUI"
    SUB_TITLE = "BlackRainLabs"
    CSS_PATH = "theme.tcss"
    COMMANDS = App.COMMANDS | {JumpProvider}
    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("a", "actions", "Actions"),
        Binding("n", "new", "New"),
        Binding("r", "reload", "Reload"),
        Binding("colon", "jump", "Jump"),
        Binding("ctrl+l", "login", "Login"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, backend: object, config: HatuiConfig) -> None:
        super().__init__()
        self.backend = backend
        self.config = config
        self.current_module = "dashboard"
        self.selected: object | None = None

    def compose(self) -> ComposeResult:
        yield OpsHeader()
        with Horizontal(id="body"):
            yield Sidebar(id="sidebar")
            yield Vertical(id="center")
            yield Inspector(id="inspector")
        yield OpsFooter()

    def on_mount(self) -> None:
        self.register_theme(BLACKRAIN)
        self.theme = "blackrain"
        self.switch_module("dashboard")
        self.set_interval(1.0, self._tick)
        if self.config.needs_login_prompt:
            self.call_after_refresh(self.action_login)

    def _tick(self) -> None:
        self.query_one(OpsHeader).refresh_status()
        self.query_one(OpsFooter).refresh_status(self.current_module)

    def switch_module(self, module_id: str) -> None:
        center = self.query_one("#center", Vertical)
        center.remove_children()
        self.selected = None
        self.current_module = module_id
        if module_id == "dashboard":
            center.mount(Dashboard(self.backend))
            self.query_one(Inspector).show(
                [
                    ("View", "Dashboard"),
                    ("Org", self.config.org_name),
                    ("Domain", self.config.domain),
                    ("Hint", "Select IDENTITY ▸ Users to start"),
                    ("Product", "BlackRainLabs HATUI"),
                ],
                "INSPECTOR",
            )
        elif module_id == "aadconnect":
            center.mount(SyncView(self.backend))
        elif module_id == "settings":
            center.mount(SettingsView(self.config))
        else:
            spec = CATALOG.get(module_id)
            if spec is None:
                self.notify(f"unknown module {module_id}", severity="error")
                return
            center.mount(ObjectBrowser(spec, self.backend))
        self.query_one(OpsFooter).refresh_status(module_id)
        self.query_one(OpsHeader).refresh_status()

    def on_navigate(self, event: Navigate) -> None:
        self.switch_module(event.module_id)

    def on_selection_changed(self, event: SelectionChanged) -> None:
        self.selected = event.obj
        title = CATALOG[event.module_id].title.upper() if event.module_id in CATALOG else "INSPECTOR"
        self.query_one(Inspector).show(event.fields, title)

    def on_activate_object(self, event: ActivateObject) -> None:
        self.selected = event.obj
        self.action_actions()

    def _browser(self) -> ObjectBrowser | None:
        found = self.query(ObjectBrowser)
        return found.first() if found else None

    def action_focus_filter(self) -> None:
        browser = self._browser()
        if browser is not None:
            browser.query_one("#filter", Input).focus()

    def action_reload(self) -> None:
        browser = self._browser()
        if browser is not None:
            browser.reload()
        elif self.current_module == "dashboard":
            self.switch_module("dashboard")
        self.query_one(OpsHeader).refresh_status()
        self.notify("reloaded")

    def action_login(self) -> None:
        preset = self.config.session_user or self.config.ldap.username or self.config.graph.username

        def _done(values: dict | None) -> None:
            if not values:
                return
            try:
                msg = self.apply_login(str(values.get("username") or ""), str(values.get("password") or ""))
            except HatuiError as exc:
                self.notify(str(exc), severity="error")
                return
            self.notify(msg)
            self.query_one(OpsHeader).refresh_status()
            self.query_one(OpsFooter).refresh_status(self.current_module)
            if self.current_module in {"connectors", "settings"}:
                self.switch_module(self.current_module)

        self.push_screen(LoginModal(preset), _done)

    def apply_login(self, username: str, password: str) -> str:
        if not username or not password:
            raise HatuiError("username and password required")
        self.config.session_user = username
        self.config.ldap.username = username
        self.config.ldap.password = password
        self.config.graph.username = username
        self.config.graph.password = password
        if self.config.ldap.auth != "bind":
            self.config.ldap.auth = "login"
        if self.config.graph.auth != "client_credentials" or not self.config.graph.client_secret:
            self.config.graph.auth = "login"
        if self.config.mode == "live":
            from hatui.services.factory import create_backend

            self.backend = create_backend(self.config)
            auth = getattr(self.backend, "authenticate", None)
            if callable(auth):
                auth()
            live = [c.name for c in self.backend.connector_status() if c.live]
            suffix = f" — {', '.join(live)}" if live else " — enable LDAP/Graph in hatui.toml"
            return f"signed in as {username}{suffix}"
        return f"signed in as {username} (mock session)"

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_jump(self) -> None:
        def _done(value: str | None) -> None:
            if not value:
                return
            target = resolve_jump(value)
            if not target:
                self.notify(f"no module '{value}'", severity="warning")
                return
            self.switch_module(target)

        self.push_screen(JumpModal(), _done)

    def action_new(self) -> None:
        self._run_named_action("new")

    def action_actions(self) -> None:
        spec = CATALOG.get(self.current_module)
        if spec is None or not spec.actions:
            if self.current_module == "aadconnect":
                self._run_sync_menu()
                return
            self.notify("no actions in this view", severity="warning")
            return
        items = [(a.id, a.label) for a in spec.actions]
        def _picked(action_id: str | None) -> None:
            if action_id:
                self._run_named_action(action_id)
        self.push_screen(ActionMenu(f"{spec.title} actions", items), _picked)

    def _run_sync_menu(self) -> None:
        def _picked(action_id: str | None) -> None:
            if not action_id:
                return
            try:
                msg = dispatch(self.backend, "aadconnect", action_id, None, {})
            except HatuiError as exc:
                self.notify(str(exc), severity="error")
                return
            self.notify(msg)
            self.switch_module("aadconnect")
        self.push_screen(ActionMenu("AAD Connect", [("delta_sync", "Delta sync"), ("full_sync", "Full sync")]), _picked)

    def _run_named_action(self, action_id: str) -> None:
        spec = CATALOG.get(self.current_module)
        if spec is None:
            self.notify("no actions here", severity="warning")
            return
        action = next((a for a in spec.actions if a.id == action_id), None)
        if action is None:
            self.notify(f"no action {action_id}", severity="warning")
            return
        if action.id == "login":
            self.action_login()
            return
        browser = self._browser()
        obj = browser.selected() if browser else self.selected
        if action.needs_selection and obj is None:
            self.notify("select a row first", severity="warning")
            return

        def _execute(values: dict[str, str] | None) -> None:
            if values is None and action.fields:
                return
            try:
                msg = dispatch(self.backend, spec.id, action.id, obj, values or {})
            except HatuiError as exc:
                self.notify(str(exc), severity="error")
                return
            self.notify(msg)
            if browser is not None:
                browser.reload()
            self.query_one(OpsHeader).refresh_status()
            self.query_one(OpsFooter).refresh_status(self.current_module)

        def _after_confirm(ok: bool | None) -> None:
            if not ok:
                return
            if action.fields:
                self.push_screen(FormModal(action.label, action.fields, danger=action.destructive), _execute)
            else:
                _execute({})

        if action.confirm:
            self.push_screen(ConfirmModal(action.label, action.confirm, danger=action.destructive), _after_confirm)
        elif action.fields:
            self.push_screen(FormModal(action.label, action.fields, danger=action.destructive), _execute)
        else:
            _execute({})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hatui", description="BlackRainLabs Hybrid Active Directory Terminal UI")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--mode", choices=["mock", "live"], default=None)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.mode:
        config.mode = args.mode
    backend = create_backend(config)
    HatuiApp(backend=backend, config=config).run()
