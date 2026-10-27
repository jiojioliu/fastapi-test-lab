from __future__ import annotations

from fastapi.testclient import TestClient


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_and_health(client: TestClient):
    page = client.get("/")
    assert page.status_code == 200
    assert "NORTHSTAR GOODS" in page.text
    assert 'id="app-shell" hidden' in page.text

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert health.json()["database"] == "ok"
    assert health.headers["X-Request-ID"].startswith("req_")

    favicon = client.get("/favicon.ico")
    assert favicon.status_code == 204
    assert favicon.content == b""


def test_login_me_and_bad_password(
    client: TestClient,
    admin_token: str,
    customer_token: str,
):
    me = client.get("/api/auth/me", headers=auth_header(admin_token))
    assert me.status_code == 200
    assert me.json()["username"] == "admin"
    assert me.json()["role"] == "admin"

    customer = client.get("/api/auth/me", headers=auth_header(customer_token))
    assert customer.status_code == 200
    assert customer.json()["username"] == "customer"
    assert customer.json()["role"] == "customer"

    bad_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "not-the-password"},
    )
    assert bad_login.status_code == 401

    retired_account = client.post(
        "/api/auth/login",
        json={"username": "tester", "password": "tester123"},
    )
    assert retired_account.status_code == 401


def test_products_support_search_sort_and_detail(client: TestClient):
    response = client.get(
        "/api/products",
        params={"search": "keyboard", "sort": "price_asc", "page_size": 20},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["category"] == "Keyboard"
    assert payload["items"][0]["price"] <= payload["items"][1]["price"]

    detail = client.get(f"/api/products/{payload['items'][0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["sku"].startswith("KB-")

    missing = client.get("/api/products/99999")
    assert missing.status_code == 404


def test_orders_require_auth_and_are_idempotent(
    client: TestClient, admin_token: str
):
    # The session-scoped TestClient keeps the login cookie. Clear it once to
    # prove the protected route rejects a request with neither cookie nor header.
    client.cookies.clear()
    unauthorized = client.get("/api/orders")
    assert unauthorized.status_code == 401
    assert unauthorized.headers["WWW-Authenticate"] == "Bearer"

    payload = {
        "items": [{"product_id": 2, "quantity": 2}],
        "note": "Automated integration test",
        "payment_method": "bank_card",
    }
    headers = {
        **auth_header(admin_token),
        "Idempotency-Key": "pytest-order-one",
    }
    first = client.post("/api/orders", json=payload, headers=headers)
    second = client.post("/api/orders", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["_idempotent_replay"] is True
    assert first.json()["items"][0]["quantity"] == 2
    assert first.json()["payment_method"] == "bank_card"
    assert first.json()["payment_status"] == "paid"

    orders = client.get("/api/orders", headers=auth_header(admin_token))
    assert orders.status_code == 200
    assert orders.json()["total"] >= 2

    invalid_payment = client.post(
        "/api/orders",
        json={
            "items": [{"product_id": 2, "quantity": 1}],
            "payment_method": "cash",
        },
        headers=auth_header(admin_token),
    )
    assert invalid_payment.status_code == 422


def test_admin_can_update_order_status(
    client: TestClient,
    customer_token: str,
    admin_token: str,
):
    created = client.post(
        "/api/orders",
        json={"items": [{"product_id": 3, "quantity": 1}]},
        headers=auth_header(customer_token),
    )
    assert created.status_code == 201
    order_id = created.json()["id"]

    forbidden = client.patch(
        f"/api/orders/{order_id}/status",
        json={"status": "shipped"},
        headers=auth_header(customer_token),
    )
    assert forbidden.status_code == 403

    updated = client.patch(
        f"/api/orders/{order_id}/status",
        json={"status": "shipped"},
        headers=auth_header(admin_token),
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "shipped"


def test_customer_orders_are_isolated_from_admin(
    client: TestClient,
    customer_token: str,
    admin_token: str,
):
    customer_orders = client.get(
        "/api/orders", headers=auth_header(customer_token)
    )
    admin_orders = client.get("/api/orders", headers=auth_header(admin_token))
    assert customer_orders.status_code == 200
    assert admin_orders.status_code == 200
    assert "ORD-SEED-CUSTOMER-0001" in {
        item["id"] for item in customer_orders.json()["items"]
    }
    assert "ORD-SEED-ADMIN-0001" in {
        item["id"] for item in admin_orders.json()["items"]
    }

    # The customer cannot read the administrator's test order.
    forbidden_customer = client.get(
        "/api/orders/ORD-SEED-ADMIN-0001", headers=auth_header(customer_token)
    )
    assert forbidden_customer.status_code == 404

    # The administrator retains cross-account visibility for management.
    admin_customer_order = client.get(
        "/api/orders/ORD-SEED-CUSTOMER-0001", headers=auth_header(admin_token)
    )
    assert admin_customer_order.status_code == 200

    lab_forbidden = client.get(
        "/api/lab/ping", headers=auth_header(customer_token)
    )
    assert lab_forbidden.status_code == 403
    admin_lab = client.get("/api/lab/ping", headers=auth_header(admin_token))
    assert admin_lab.status_code == 200


def test_guest_is_read_only_and_registration_creates_customer(
    client: TestClient,
    guest_token: str,
):
    guest = client.get("/api/auth/me", headers=auth_header(guest_token))
    assert guest.status_code == 200
    assert guest.json()["role"] == "guest"

    orders = client.get("/api/orders", headers=auth_header(guest_token))
    assert orders.status_code == 403
    lab = client.get("/api/lab/ping", headers=auth_header(guest_token))
    assert lab.status_code == 403

    registration = client.post(
        "/api/auth/register",
        json={
            "username": "new_customer",
            "password": "strong-password",
            "display_name": "New Customer",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["user"]["role"] == "customer"


def test_form_upload_and_echo(client: TestClient, admin_token: str):
    headers = auth_header(admin_token)
    form = client.post(
        "/api/lab/form",
        headers=headers,
        data={
            "name": "API Tester",
            "email": "admin@example.test",
            "subject": "Form exercise",
            "message": "This request uses x-www-form-urlencoded.",
        },
    )
    assert form.status_code == 200
    assert form.json()["ok"] is True

    upload = client.post(
        "/api/lab/upload",
        headers=headers,
        files={"file": ("hello.txt", b"fastapi test lab", "text/plain")},
    )
    assert upload.status_code == 201
    assert upload.json()["size_bytes"] == 16
    assert len(upload.json()["sha256"]) == 64

    echo = client.post(
        "/api/lab/echo?mode=test",
        headers={**headers, "X-Custom-Header": "observable"},
        json={"hello": "lab"},
    )
    assert echo.status_code == 200
    assert echo.json()["query"] == {"mode": "test"}
    assert echo.json()["headers"]["x-custom-header"] == "observable"
    assert echo.json()["body"] == {"hello": "lab"}


def test_simulated_status_and_rate_limit(
    client: TestClient, admin_token: str
):
    headers = auth_header(admin_token)
    for code in (400, 401, 403, 404, 429, 500, 503):
        response = client.get(f"/api/lab/status/{code}", headers=headers)
        assert response.status_code == code
        assert response.json()["simulated_status"] == code

    headers = {**headers, "X-Lab-Client": "pytest-burst"}
    statuses = [
        client.get("/api/lab/rate-limit", headers=headers).status_code
        for _ in range(6)
    ]
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


def test_traffic_metrics_capture_activity(
    client: TestClient, admin_token: str
):
    headers = auth_header(admin_token)
    client.get("/api/lab/ping", headers=headers)
    response = client.get("/api/traffic/summary", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_requests"] > 0
    assert len(payload["timeline"]) == 15
    assert isinstance(payload["recent"], list)

