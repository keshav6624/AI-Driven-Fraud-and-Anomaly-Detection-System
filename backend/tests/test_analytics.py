"""Tests for analytics endpoints."""
from __future__ import annotations


def test_overview(client, auth_headers):
    r = client.get("/analytics/overview", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_members" in data
    assert "risk_distribution" in data


def test_risk_distribution(client, auth_headers):
    r = client.get("/analytics/risk-distribution", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "LOW" in data
    assert "HIGH" in data


def test_anomaly_scatter(client, auth_headers):
    r = client.get("/analytics/anomaly/scatter", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_anomaly_distribution(client, auth_headers):
    r = client.get("/analytics/anomaly/distribution", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "bins" in data
    assert "counts" in data


def test_duplicate_summary(client, auth_headers):
    r = client.get("/analytics/duplicates/summary", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_pairs" in data
    assert "flagged_pairs" in data


def test_list_duplicates(client, auth_headers):
    r = client.get("/analytics/duplicates?page_size=10", headers=auth_headers)
    assert r.status_code == 200
    assert "items" in r.json()
