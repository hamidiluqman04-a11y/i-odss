import pytest
from django.contrib.auth import get_user_model
from django.test import Client

PASSWORD = "a-strong-test-pass-123"


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="seller@example.com", email="seller@example.com", password=PASSWORD, first_name="Siti"
    )


def login(client, email="seller@example.com", password=PASSWORD):
    return client.post("/api/auth/login/", {"email": email, "password": password}, content_type="application/json")


def test_login_success_returns_user_and_session(client, user):
    r = login(client)
    assert r.status_code == 200
    assert r.json() == {"user": {"id": user.id, "email": "seller@example.com", "name": "Siti"}}
    assert client.get("/api/auth/me/").status_code == 200


def test_login_email_is_case_insensitive(client, user):
    assert login(client, email="Seller@Example.COM").status_code == 200


def test_wrong_password_gives_generic_401(client, user):
    r = login(client, password="wrong")
    assert r.status_code == 401
    assert r.json() == {"error": {"type": "invalid_credentials", "message": "Invalid email or password."}}


def test_unknown_email_gives_same_message(client, db):
    assert login(client, email="nobody@example.com").json()["error"]["type"] == "invalid_credentials"


def test_login_validates_input(client, db):
    r = client.post("/api/auth/login/", {"email": "not-an-email"}, content_type="application/json")
    assert r.status_code == 400
    body = r.json()["error"]
    assert body["type"] == "validation_error"
    assert set(body["details"]) == {"email", "password"}


def test_me_requires_login(client, db):
    r = client.get("/api/auth/me/")
    assert r.status_code == 403
    assert r.json()["error"]["type"] == "not_authenticated"


def test_logout_ends_session(client, user):
    login(client)
    assert client.post("/api/auth/logout/").status_code == 204
    assert client.get("/api/auth/me/").status_code == 403


def test_register_creates_hashed_user_and_logs_in(client, db):
    r = client.post(
        "/api/auth/register/",
        {"name": "Ali", "email": "Ali@Shop.my", "password": "kopi-susu-2025!"},
        content_type="application/json",
    )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "ali@shop.my"
    stored = get_user_model().objects.get(username="ali@shop.my")
    assert stored.password != "kopi-susu-2025!" and stored.check_password("kopi-susu-2025!")
    assert client.get("/api/auth/me/").status_code == 200


def test_register_rejects_weak_password_and_duplicate_email(client, user):
    weak = client.post("/api/auth/register/", {"name": "A", "email": "a@b.co", "password": "12345678"},
                       content_type="application/json")
    assert weak.status_code == 400
    dup = client.post("/api/auth/register/", {"name": "A", "email": "seller@example.com", "password": "kopi-susu-2025!"},
                      content_type="application/json")
    assert dup.status_code == 400
    assert "already exists" in str(dup.json()["error"]["details"]["email"])


def test_login_and_logout_require_csrf_token(user):
    strict = Client(enforce_csrf_checks=True)
    assert login(strict).status_code == 403                       # no token yet

    strict.get("/api/auth/csrf/")
    token = strict.cookies["csrftoken"].value
    r = strict.post("/api/auth/login/", {"email": "seller@example.com", "password": PASSWORD},
                    content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 200

    token = strict.cookies["csrftoken"].value                     # rotated on login
    assert strict.post("/api/auth/logout/").status_code == 403
    assert strict.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code == 204


def test_repeated_login_attempts_are_rate_limited(client, user):
    for _ in range(10):
        assert login(client, password="wrong").status_code == 401
    r = login(client)                       # even the right password is refused for now
    assert r.status_code == 429
    body = r.json()["error"]
    assert body["type"] == "throttled"
    assert body["message"].startswith("Too many attempts. Please wait")
    assert "Retry-After" in r.headers


def test_rate_limit_is_per_ip_address(client, user):
    for _ in range(10):
        login(client, password="wrong")
    other_ip = client.post("/api/auth/login/", {"email": "seller@example.com", "password": PASSWORD},
                           content_type="application/json", REMOTE_ADDR="10.0.0.2")
    assert other_ip.status_code == 200


def test_registration_is_rate_limited(client, db):
    for i in range(5):
        client.post("/api/auth/register/", {"name": "A", "email": f"user{i}@shop.my", "password": "kopi-susu-2025!"},
                    content_type="application/json")
        client.logout()
    r = client.post("/api/auth/register/", {"name": "A", "email": "user9@shop.my", "password": "kopi-susu-2025!"},
                    content_type="application/json")
    assert r.status_code == 429


def test_session_cookie_is_httponly(client, user):
    login(client)
    assert client.cookies["sessionid"]["httponly"]
