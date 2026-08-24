"""Tests for authentication endpoints."""
from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_success(client, seed_users):
    r = client.post("/auth/login", json={"username": "testadmin", "password": "testpass123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"
    assert data["username"] == "testadmin"


def test_login_wrong_password(client, seed_users):
    r = client.post("/auth/login", json={"username": "testadmin", "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    r = client.post("/auth/login", json={"username": "nouser", "password": "testpass123"})
    assert r.status_code == 401


def test_protected_route_without_token(client):
    r = client.get("/projects")
    assert r.status_code == 401 or r.status_code == 403


def test_list_users(client, auth_headers):
    r = client.get("/auth/users", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_user(client, auth_headers):
    r = client.post("/auth/users", json={
        "username": "newanalyst",
        "password": "password123",
        "full_name": "New Analyst",
        "role": "ANALYST",
    }, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["username"] == "newanalyst"
    assert r.json()["role"] == "ANALYST"


def test_create_duplicate_user(client, auth_headers):
    r = client.post("/auth/users", json={
        "username": "testadmin",
        "password": "password123",
        "full_name": "Duplicate",
        "role": "VIEWER",
    }, headers=auth_headers)
    assert r.status_code == 409
