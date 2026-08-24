"""Tests for investigation case endpoints."""
from __future__ import annotations


def test_list_cases_empty(client, auth_headers):
    r = client.get("/investigations", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_create_case(client, auth_headers):
    r = client.post("/investigations", json={
        "member_id": 1,
        "title": "Test Investigation",
        "description": "Testing case creation",
        "priority": "HIGH",
    }, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test Investigation"
    assert data["status"] == "OPEN"
    assert data["priority"] == "HIGH"


def test_get_case(client, auth_headers):
    # Create first
    r = client.post("/investigations", json={
        "member_id": 1,
        "title": "Get Test",
    }, headers=auth_headers)
    case_id = r.json()["case_id"]

    r = client.get(f"/investigations/{case_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["case_id"] == case_id


def test_update_case_status(client, auth_headers):
    r = client.post("/investigations", json={
        "member_id": 1,
        "title": "Update Test",
    }, headers=auth_headers)
    case_id = r.json()["case_id"]

    r = client.patch(f"/investigations/{case_id}", json={"status": "UNDER_REVIEW"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "UNDER_REVIEW"


def test_add_note(client, auth_headers):
    r = client.post("/investigations", json={
        "member_id": 1,
        "title": "Note Test",
    }, headers=auth_headers)
    case_id = r.json()["case_id"]

    r = client.post(f"/investigations/{case_id}/notes", json={"body": "Test note"}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["body"] == "Test note"


def test_get_nonexistent_case(client, auth_headers):
    r = client.get("/investigations/99999", headers=auth_headers)
    assert r.status_code == 404
