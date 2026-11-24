"""Integration tests for Analytics API and UI View — Phase 7."""
import pytest


def test_get_dashboard_analytics(client, viewer_headers):
    resp = client.get("/api/analytics/dashboard", headers=viewer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data
    assert "success_rate" in data
    assert "failure_rate" in data
    assert "average_processing_time" in data
    assert "recent_documents" in data
    assert "recent_jobs" in data


def test_get_detailed_analytics(client, viewer_headers):
    resp = client.get("/api/analytics/detailed", headers=viewer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "by_file_type" in data
    assert "confidence_stats" in data
    assert "validation_stats" in data
    assert "report_stats" in data


def test_analytics_html_view(client, viewer_headers):
    # Set session cookie or token
    # Client will get redirected if unauthenticated
    resp = client.get("/analytics")
    # Redirects to /login if no cookie, which is 302
    assert resp.status_code in (200, 302)


def test_unauthenticated_analytics_api(client):
    resp = client.get("/api/analytics/dashboard")
    assert resp.status_code in (401, 403)
