from unittest import mock

import pytest
from django.db.utils import OperationalError


@pytest.mark.django_db
def test_health_ok_when_database_reachable(client):
    r = client.get("/api/health/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_health_reports_503_without_leaking_details(client):
    secret_message = 'connection to server at "localhost" failed: password authentication failed'
    with mock.patch("config.views.connection.cursor", side_effect=OperationalError(secret_message)):
        r = client.get("/api/health/")
    assert r.status_code == 503
    assert r.json() == {"status": "error", "database": "unavailable"}
    assert "password" not in r.content.decode()


def test_health_rejects_post(client):
    assert client.post("/api/health/").status_code == 405
