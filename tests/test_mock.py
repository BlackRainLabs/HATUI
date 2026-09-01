from hatui.models import MailboxRight, MailboxType
from hatui.services.mock.backend import MockBackend
from hatui.services.protocol import HatuiError


def test_seed_counts():
    be = MockBackend()
    assert len(be.list_users()) >= 80
    assert len(be.list_mailboxes()) >= 40
    assert len(be.list_groups()) >= 10
    assert len(be.list_ous()) >= 8
    assert len(be.list_dcs()) == 3
    assert len(be.list_fsmo()) == 5
    health = be.forest_health()
    assert health.domain == "blackrainlabs.corp"
    assert health.mode == "MOCK"
    assert health.users >= 80


def test_named_cast_and_edge_cases():
    be = MockBackend()
    names = {u.display_name for u in be.list_users()}
    assert "Elena Voss" in names
    assert "Lumen Cho" in names
    locked = next(u for u in be.list_users() if u.display_name == "Locke Dray")
    assert locked.locked
    dormant = next(u for u in be.list_users() if u.display_name == "Dormant Wells")
    assert not dormant.enabled
    assert dormant.mailbox_id is None
    orphan = next(u for u in be.list_users() if u.display_name == "Orphan Mail")
    assert orphan.mailbox_id
    mb = be.get_mailbox(orphan.mailbox_id)
    assert mb.licensed is False
    drift = next(u for u in be.list_users() if u.display_name == "Drift Sync")
    assert drift.sync_error
    assert be.list_guests()


def test_create_user_enable_mailbox_grant_permission():
    be = MockBackend()
    user = be.create_user(given_name="Nova", surname="Pike", department="Security", origin="synced")
    assert user.upn.endswith("@blackrainlabs.corp")
    assert user.mailbox_id is None
    mb = be.enable_mailbox(user.id)
    assert mb.mailbox_type == MailboxType.REMOTE
    assert be.get_user(user.id).mailbox_id == mb.id
    trustee = next(u for u in be.list_users() if u.display_name == "Elena Voss")
    perm = be.grant_permission(mb.id, trustee.upn, MailboxRight.FULL_ACCESS)
    assert perm.trustee == trustee.upn
    assert any(p.id == perm.id for p in be.list_permissions(mb.id))
    be.revoke_permission(perm.id)
    assert all(p.id != perm.id for p in be.list_permissions(mb.id))


def test_unlock_reset_disable():
    be = MockBackend()
    locked = next(u for u in be.list_users() if u.locked)
    be.unlock_user(locked.id)
    assert be.get_user(locked.id).locked is False
    be.reset_password(locked.id, "Tmp-test-0001!", True)
    assert be.get_user(locked.id).must_change_password is True
    be.set_user_enabled(locked.id, False)
    assert be.get_user(locked.id).enabled is False


def test_sync_and_jobs():
    be = MockBackend()
    before = len(be.list_jobs())
    st = be.run_delta_sync()
    assert st.exported > 0
    assert len(be.list_jobs()) > before
    assert be.list_audit()


def test_licenses_and_restore():
    be = MockBackend()
    user = be.create_user(given_name="Sky", surname="Watt", origin="cloud-only")
    be.assign_license(user.id, "SPE_E3")
    assert "SPE_E3" in be.get_user(user.id).licenses
    deleted = be.list_soft_deleted()[0]
    restored = be.restore_deleted(deleted.id)
    assert restored.display_name == deleted.display_name


def test_group_membership_and_gpo():
    be = MockBackend()
    user = next(u for u in be.list_users() if u.display_name == "Kade Morrow")
    be.add_group_member("g-da", user.id)
    da = next(g for g in be.list_groups() if g.id == "g-da")
    assert user.id in da.member_ids
    gpo = be.list_gpos()[0]
    be.set_gpo_enabled(gpo.id, False)
    updated = next(g for g in be.list_gpos() if g.id == gpo.id)
    assert updated.enabled is False


def test_unknown_user():
    be = MockBackend()
    try:
        be.get_user("nope")
        raise AssertionError("expected error")
    except HatuiError:
        pass
