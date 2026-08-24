"""Tests for project endpoints."""
from __future__ import annotations


def test_list_projects(client, auth_headers):
    r = client.get("/projects?page=1&page_size=5", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


def test_get_project_not_found(client, auth_headers):
    r = client.get("/projects/99999", headers=auth_headers)
    assert r.status_code == 404


def test_list_states(client, auth_headers):
    r = client.get("/projects/meta/states", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_map_points(client, auth_headers):
    r = client.get("/map/projects", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_projects_search(client, auth_headers):
    r = client.get("/projects?search=Delhi&page_size=5", headers=auth_headers)
    assert r.status_code == 200


def test_projects_filter_risk(client, auth_headers):
    r = client.get("/projects?risk_level=LOW&page_size=5", headers=auth_headers)
    assert r.status_code == 200
