def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "DocuFlow"


def test_login_success(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin@123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "admin"
    assert "access_token" in response.cookies


def test_login_invalid_password(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    response = client.post("/api/auth/login", json={
        "email": "nobody@test.com",
        "password": "Admin@123"
    })
    assert response.status_code == 401


def test_get_me_authenticated(client, admin_headers):
    response = client.get("/api/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


def test_get_me_unauthenticated(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_admin_register_user(client, admin_headers):
    response = client.post("/api/auth/register", headers=admin_headers, json={
        "name": "New Team Member",
        "email": "teammate@test.com",
        "password": "Password@123",
        "role": "processing_manager"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "teammate@test.com"
    assert data["role"] == "processing_manager"


def test_manager_cannot_register_user(client, manager_headers):
    response = client.post("/api/auth/register", headers=manager_headers, json={
        "name": "Unauthorized User",
        "email": "unauth@test.com",
        "password": "Password@123",
        "role": "viewer"
    })
    assert response.status_code == 403


def test_logout(client, admin_headers):
    response = client.post("/api/auth/logout", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out."
