"""Production serving of the built React app by Django."""
from django.test import override_settings


def test_page_addresses_return_the_react_app(client, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    with override_settings(FRONTEND_DIST=tmp_path):
        for path in ["/", "/forecast", "/pricing", "/upload"]:
            r = client.get(path)
            assert r.status_code == 200, path
            assert b'<div id=root>' in b"".join(r.streaming_content)
            assert r["Content-Type"] == "text/html"
            assert r["Cache-Control"] == "no-cache"


def test_api_addresses_are_never_answered_with_the_react_app(client, tmp_path, db):
    (tmp_path / "index.html").write_text("<!doctype html>", encoding="utf-8")
    with override_settings(FRONTEND_DIST=tmp_path):
        assert client.get("/api/does-not-exist/").status_code == 404
        assert client.get("/api/health/").json()["service"] == "I-ODSS"


def test_without_a_build_page_addresses_are_404(client, tmp_path):
    with override_settings(FRONTEND_DIST=tmp_path / "missing"):
        assert client.get("/forecast").status_code == 404
