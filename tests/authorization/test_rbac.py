def test_admin_can_list_users(client, admin_headers):
    response = client.get("/api/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 3


def test_manager_cannot_list_users(client, manager_headers):
    response = client.get("/api/users", headers=manager_headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_viewer_cannot_list_users(client, viewer_headers):
    response = client.get("/api/users", headers=viewer_headers)
    assert response.status_code == 403


def test_unauthenticated_cannot_list_users(client):
    response = client.get("/api/users")
    assert response.status_code == 401


def test_authenticated_can_access_analytics(client, viewer_headers):
    response = client.get("/api/analytics/dashboard", headers=viewer_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "successfully_processed" in data
    assert "average_processing_time" in data


def test_unauthenticated_cannot_access_analytics(client):
    response = client.get("/api/analytics/dashboard")
    assert response.status_code == 401
