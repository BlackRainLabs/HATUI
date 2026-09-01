from __future__ import annotations

from dataclasses import dataclass, field

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Select, Static
from textual.widgets.option_list import Option


@dataclass
class FieldSpec:
    name: str
    label: str
    kind: str = "input"
    options: list[tuple[str, str]] = field(default_factory=list)
    default: str = ""
    placeholder: str = ""


class FormModal(ModalScreen[dict | None]):
    def __init__(self, title: str, fields: list[FieldSpec], danger: bool = False) -> None:
        super().__init__()
        self.form_title = title
        self.fields = fields
        self.danger = danger

    def compose(self) -> ComposeResult:
        classes = "danger" if self.danger else ""
        with Vertical(id="modal", classes=classes):
            yield Static(self.form_title, id="modal-title")
            for spec in self.fields:
                yield Label(spec.label)
                wid = f"f-{spec.name}"
                if spec.kind == "select" and spec.options:
                    yield Select(spec.options, id=wid, allow_blank=False, value=spec.default or spec.options[0][1])
                elif spec.kind == "password":
                    yield Input(value=spec.default, placeholder=spec.placeholder or spec.label, id=wid, password=True)
                else:
                    yield Input(value=spec.default, placeholder=spec.placeholder or spec.label, id=wid)
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Commit", id="ok", classes="danger" if self.danger else "primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        values: dict[str, str] = {}
        for spec in self.fields:
            widget = self.query_one(f"#f-{spec.name}")
            values[spec.name] = str(getattr(widget, "value", "") or "")
        self.dismiss(values)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#ok", Button).press()


class ConfirmModal(ModalScreen[bool]):
    def __init__(self, title: str, body: str, danger: bool = True) -> None:
        super().__init__()
        self.form_title = title
        self.body = body
        self.danger = danger

    def compose(self) -> ComposeResult:
        classes = "danger" if self.danger else ""
        with Vertical(id="modal", classes=classes):
            yield Static(self.form_title, id="modal-title")
            yield Static(self.body)
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Confirm", id="ok", classes="danger" if self.danger else "primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "ok")


class ActionOptionList(OptionList):
    """Activate on click; ignore the second pulse of a double-click so the menu is not dismissed twice."""

    async def _on_click(self, event: Click) -> None:
        if event.chain > 1:
            event.stop()
            return
        clicked_option: int | None = event.style.meta.get("option")
        if clicked_option is None:
            return
        option = self._options[clicked_option]
        if option.disabled:
            return
        self.highlighted = clicked_option
        self.action_select()
        event.stop()


class ActionMenu(ModalScreen[str | None]):
    def __init__(self, title: str, actions: list[tuple[str, str]]) -> None:
        super().__init__()
        self.form_title = title
        self.actions = actions
        self._closed = False

    def compose(self) -> ComposeResult:
        with Vertical(id="modal"):
            yield Static(self.form_title, id="modal-title")
            yield ActionOptionList(*[Option(label, id=aid) for aid, label in self.actions], id="action-list")
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel")

    def _close(self, result: str | None) -> None:
        if self._closed or not self.is_current:
            return
        self._closed = True
        self.dismiss(result)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        self._close(event.option_id or (str(event.option.id) if event.option.id else None))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._close(None)


class LoginModal(ModalScreen[dict | None]):
    def __init__(self, username: str = "") -> None:
        super().__init__()
        self.username = username

    def compose(self) -> ComposeResult:
        with Vertical(id="modal"):
            yield Static("SIGN IN", id="modal-title")
            yield Static("LDAP bind and Graph login use this operator identity.")
            yield Label("Username (UPN or DOMAIN\\user)")
            yield Input(value=self.username, placeholder="admin@blackrainlabs.corp", id="login-user")
            yield Label("Password")
            yield Input(placeholder="password", id="login-pass", password=True)
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Sign in", id="ok", classes="primary")

    def on_mount(self) -> None:
        target = "#login-pass" if self.username else "#login-user"
        self.query_one(target, Input).focus()

    def _values(self) -> dict[str, str]:
        return {
            "username": self.query_one("#login-user", Input).value.strip(),
            "password": self.query_one("#login-pass", Input).value,
        }

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "login-user":
            self.query_one("#login-pass", Input).focus()
            return
        self.dismiss(self._values())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self._values())
        else:
            self.dismiss(None)


class JumpModal(ModalScreen[str | None]):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal"):
            yield Static("JUMP", id="modal-title")
            yield Input(placeholder="users | mailboxes | sync | gpos …", id="jump")
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Go", id="ok", classes="primary")

    def on_mount(self) -> None:
        self.query_one("#jump", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one("#jump", Input).value.strip())
        else:
            self.dismiss(None)


class HelpScreen(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        with VerticalScroll(id="modal"):
            yield Static("BLACKRAINLABS  //  HATUI", id="modal-title")
            yield Static(
                "[b]F1[/] help    [b]/[/] filter    [b]a[/] actions    [b]n[/] new\n"
                "[b]r[/] reload   [b]:[/] jump      [b]Ctrl+L[/] login    [b]Ctrl+P[/] palette    [b]q[/] quit\n\n"
                "[b]IDENTITY[/]  users groups computers contacts gMSA\n"
                "[b]DIRECTORY[/] OUs DCs FSMO sites GPOs replication trusts\n"
                "[b]EXCHANGE[/]  mailboxes permissions recipients DLs resources mail-flow\n"
                "[b]ENTRA[/]     cloud users guests licenses roles AAD Connect recycle bin\n"
                "[b]SECURITY[/]  lockout/password privileged groups\n"
                "[b]OPS[/]       jobs audit connectors settings\n\n"
                "Default forest is mock [b]BlackRainLabs[/] / blackrainlabs.corp.\n"
                "Ctrl+L signs into LDAP (user bind) and Graph (password grant).\n"
                "Live LDAP + Graph light up on the status bar when configured.\n\n"
                "Press [b]Esc[/] to close. Double-click a row (or Enter) to open actions;\n"
                "click or double-click an action to run it."
            )

    def on_key(self, event) -> None:
        if event.key in {"escape", "f1", "q"}:
            self.dismiss(None)
            event.stop()
