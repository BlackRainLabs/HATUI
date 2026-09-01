import pytest

from textual.widgets import Static

from hatui.app import HatuiApp
from hatui.config import load_config
from hatui.models import MailboxRight
from hatui.services.factory import create_backend
from hatui.ui.actions import dispatch
from hatui.ui.browser import ObjectBrowser
from hatui.ui.catalog import CATALOG
from hatui.ui.screens import Dashboard, SettingsView, SyncView


@pytest.mark.asyncio
async def test_app_dashboard_and_users():
    config = load_config()
    backend = create_backend(config)
    app = HatuiApp(backend=backend, config=config)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_module == "dashboard"
        assert app.query_one(Dashboard)
        assert app.theme == "blackrain"
        assert config.org_name == "BlackRainLabs"
        assert app.query_one("#brand", Static).content == "BRL"
        assert app.query_one("#product", Static).content == "HATUI"
        assert "BlackRainLabs" in str(app.query_one("#org", Static).content)
        msg = app.apply_login("ops@blackrainlabs.corp", "dummy-pass")
        assert "ops@blackrainlabs.corp" in msg
        assert app.config.ldap.auth == "login"
        assert app.config.graph.auth == "login"
        assert app.config.session_user == "ops@blackrainlabs.corp"
        app.switch_module("users")
        await pilot.pause()
        browser = app.query_one(ObjectBrowser)
        assert browser.spec.id == "users"
        assert len(browser.rows) >= 80
        app.switch_module("mailboxes")
        await pilot.pause()
        browser = app.query_one(ObjectBrowser)
        assert browser.spec.id == "mailboxes"
        assert len(browser.rows) >= 40
        app.switch_module("permissions")
        await pilot.pause()
        assert app.query_one(ObjectBrowser).spec.id == "permissions"


@pytest.mark.asyncio
async def test_row_activate_opens_action_menu():
    from textual.widgets import DataTable, OptionList

    from hatui.ui.modals import ActionMenu

    config = load_config()
    app = HatuiApp(backend=create_backend(config), config=config)
    async with app.run_test() as pilot:
        app.switch_module("mailboxes")
        await pilot.pause()
        table = app.query_one("#table", DataTable)
        table.action_select_cursor()
        await pilot.pause()
        assert isinstance(app.screen, ActionMenu)
        opt_list = app.screen.query_one("#action-list", OptionList)
        option = opt_list.get_option("autoreply_on")
        index = opt_list.get_option_index("autoreply_on")
        opt_list.post_message(OptionList.OptionSelected(opt_list, option, index))
        opt_list.post_message(OptionList.OptionSelected(opt_list, option, index))
        await pilot.pause()
        assert not isinstance(app.screen, ActionMenu)


@pytest.mark.asyncio
async def test_all_modules_and_mailbox_workflow():
    config = load_config()
    backend = create_backend(config)
    app = HatuiApp(backend=backend, config=config)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.switch_module("aadconnect")
        await pilot.pause()
        assert app.query_one(SyncView)
        app.switch_module("settings")
        await pilot.pause()
        assert app.query_one(SettingsView)
        for module_id in CATALOG:
            app.switch_module(module_id)
            await pilot.pause()
            assert app.query_one(ObjectBrowser).spec.id == module_id

        msg = dispatch(
            app.backend,
            "users",
            "new",
            None,
            {
                "given_name": "Ada",
                "surname": "Lovelace",
                "department": "Engineering",
                "title": "Analyst",
                "origin": "synced",
            },
        )
        assert "ada.lovelace" in msg.lower() or "alovelace" in msg.lower()
        created = next(u for u in app.backend.list_users() if u.surname == "Lovelace")
        mb = dispatch(
            app.backend,
            "users",
            "enable_mailbox",
            created,
            {"mailbox_type": "RemoteMailbox"},
        )
        assert "RemoteMailbox" in mb
        trustee = next(u for u in app.backend.list_users() if u.display_name == "Elena Voss")
        created = app.backend.get_user(created.id)
        grant = dispatch(
            app.backend,
            "mailboxes",
            "grant",
            app.backend.get_mailbox(created.mailbox_id),
            {"trustee": trustee.upn, "rights": MailboxRight.FULL_ACCESS.value, "automapping": "Y"},
        )
        assert "FullAccess" in grant
        app.switch_module("permissions")
        await pilot.pause()
        browser = app.query_one(ObjectBrowser)
        assert any(
            getattr(obj, "trustee", None) == trustee.upn and getattr(obj, "mailbox_id", None) == created.mailbox_id
            for obj in browser.rows.values()
        )
