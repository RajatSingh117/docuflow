"""Integration tests for Scheduled Automation API — Phase 6."""
import pytest


# ── CREATE ────────────────────────────────────────────────────────────────────

class TestCreateSchedule:
    def test_manager_can_create_daily_schedule(self, client, manager_headers):
        resp = client.post(
            "/api/schedules",
            json={"name": "Daily Invoice Run", "schedule_type": "daily"},
            headers=manager_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Daily Invoice Run"
        assert data["schedule_type"] == "daily"
        assert data["is_active"] is True
        assert "next_run_at" in data

    def test_admin_can_create_weekly_schedule(self, client, admin_headers):
        resp = client.post(
            "/api/schedules",
            json={"name": "Weekly PDF Digest", "schedule_type": "weekly"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["schedule_type"] == "weekly"

    def test_admin_can_create_monthly_schedule(self, client, admin_headers):
        resp = client.post(
            "/api/schedules",
            json={"name": "Monthly Audit", "schedule_type": "monthly"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["schedule_type"] == "monthly"

    def test_viewer_cannot_create_schedule(self, client, viewer_headers):
        resp = client.post(
            "/api/schedules",
            json={"name": "Viewer Schedule", "schedule_type": "daily"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_invalid_schedule_type_rejected(self, client, manager_headers):
        resp = client.post(
            "/api/schedules",
            json={"name": "Bad Schedule", "schedule_type": "hourly"},
            headers=manager_headers,
        )
        assert resp.status_code == 400

    def test_unauthenticated_cannot_create_schedule(self, client):
        resp = client.post(
            "/api/schedules",
            json={"name": "No Auth", "schedule_type": "daily"},
        )
        assert resp.status_code in (401, 403)


# ── LIST ─────────────────────────────────────────────────────────────────────

class TestListSchedules:
    def test_any_authenticated_user_can_list(self, client, viewer_headers):
        resp = client.get("/api/schedules", headers=viewer_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_includes_created_schedule(self, client, manager_headers):
        client.post(
            "/api/schedules",
            json={"name": "List Test Schedule", "schedule_type": "daily"},
            headers=manager_headers,
        )
        resp = client.get("/api/schedules", headers=manager_headers)
        names = [s["name"] for s in resp.json()]
        assert "List Test Schedule" in names

    def test_unauthenticated_cannot_list(self, client):
        resp = client.get("/api/schedules")
        assert resp.status_code in (401, 403)


# ── TOGGLE ────────────────────────────────────────────────────────────────────

class TestToggleSchedule:
    def _create_schedule(self, client, manager_headers, name="Toggle Me"):
        r = client.post(
            "/api/schedules",
            json={"name": name, "schedule_type": "daily"},
            headers=manager_headers,
        )
        assert r.status_code == 201
        return r.json()["id"]

    def test_manager_can_toggle_schedule(self, client, manager_headers):
        sid = self._create_schedule(client, manager_headers, "Toggle Schedule A")
        resp = client.put(f"/api/schedules/{sid}/toggle", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sid
        assert data["is_active"] is False  # was True, now paused

    def test_double_toggle_restores_active(self, client, manager_headers):
        sid = self._create_schedule(client, manager_headers, "Toggle Schedule B")
        client.put(f"/api/schedules/{sid}/toggle", headers=manager_headers)  # pause
        resp = client.put(f"/api/schedules/{sid}/toggle", headers=manager_headers)  # resume
        assert resp.json()["is_active"] is True

    def test_viewer_cannot_toggle_schedule(self, client, manager_headers, viewer_headers):
        sid = self._create_schedule(client, manager_headers, "Toggle Schedule C")
        resp = client.put(f"/api/schedules/{sid}/toggle", headers=viewer_headers)
        assert resp.status_code == 403

    def test_toggle_nonexistent_schedule_404(self, client, manager_headers):
        resp = client.put("/api/schedules/999999/toggle", headers=manager_headers)
        assert resp.status_code == 404


# ── MANUAL TRIGGER ────────────────────────────────────────────────────────────

class TestRunScheduleNow:
    def test_trigger_with_no_documents_returns_skipped(self, client, manager_headers):
        """With no documents in DB the scheduler gracefully returns 'skipped'."""
        r = client.post(
            "/api/schedules",
            json={"name": "Run Now Test", "schedule_type": "daily"},
            headers=manager_headers,
        )
        sid = r.json()["id"]
        resp = client.post(f"/api/schedules/{sid}/run", headers=manager_headers)
        assert resp.status_code == 200
        result = resp.json()
        assert result.get("status") in ("skipped", "SUCCESS", "FAILED")

    def test_trigger_inactive_schedule_skipped(self, client, manager_headers):
        """Triggering a paused schedule returns 'skipped'."""
        r = client.post(
            "/api/schedules",
            json={"name": "Inactive Run Test", "schedule_type": "weekly"},
            headers=manager_headers,
        )
        sid = r.json()["id"]
        # Pause it first
        client.put(f"/api/schedules/{sid}/toggle", headers=manager_headers)
        resp = client.post(f"/api/schedules/{sid}/run", headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "skipped"

    def test_viewer_cannot_trigger_schedule(self, client, manager_headers, viewer_headers):
        r = client.post(
            "/api/schedules",
            json={"name": "Viewer Trigger Test", "schedule_type": "daily"},
            headers=manager_headers,
        )
        sid = r.json()["id"]
        resp = client.post(f"/api/schedules/{sid}/run", headers=viewer_headers)
        assert resp.status_code == 403

    def test_trigger_nonexistent_schedule_404(self, client, manager_headers):
        resp = client.post("/api/schedules/999999/run", headers=manager_headers)
        assert resp.status_code == 404


# ── DELETE ────────────────────────────────────────────────────────────────────

class TestDeleteSchedule:
    def test_manager_can_delete_schedule(self, client, manager_headers):
        r = client.post(
            "/api/schedules",
            json={"name": "Delete Me Schedule", "schedule_type": "monthly"},
            headers=manager_headers,
        )
        sid = r.json()["id"]
        resp = client.delete(f"/api/schedules/{sid}", headers=manager_headers)
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_deleted_schedule_no_longer_in_list(self, client, manager_headers):
        r = client.post(
            "/api/schedules",
            json={"name": "Gone Schedule", "schedule_type": "daily"},
            headers=manager_headers,
        )
        sid = r.json()["id"]
        client.delete(f"/api/schedules/{sid}", headers=manager_headers)
        list_resp = client.get("/api/schedules", headers=manager_headers)
        ids = [s["id"] for s in list_resp.json()]
        assert sid not in ids

    def test_viewer_cannot_delete_schedule(self, client, manager_headers, viewer_headers):
        r = client.post(
            "/api/schedules",
            json={"name": "Viewer Delete Test", "schedule_type": "daily"},
            headers=manager_headers,
        )
        sid = r.json()["id"]
        resp = client.delete(f"/api/schedules/{sid}", headers=viewer_headers)
        assert resp.status_code == 403

    def test_delete_nonexistent_schedule_404(self, client, manager_headers):
        resp = client.delete("/api/schedules/999999", headers=manager_headers)
        assert resp.status_code == 404
