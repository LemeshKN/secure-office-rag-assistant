import pytest

URL = "/cost/admin/seats"
HEADER = "user_name,department,seat_type,assigned_date,last_active_date,messages_last_30_days\n"


def upload(client, headers, content, **data):
    return client.post(f"{URL}/analyze", files={"file": ("seats.csv", content, "text/csv")},
                       data=data, headers=headers)


@pytest.mark.parametrize("method, path", [("get", "/sample"), ("post", "/analyze")])
def test_seat_endpoints_are_admin_only(cost_client, auth_headers, method, path):
    call = getattr(cost_client, method)
    kwargs = {"files": {"file": ("seats.csv", HEADER, "text/csv")}} if method == "post" else {}
    assert call(f"{URL}{path}", **kwargs).status_code == 401
    assert call(f"{URL}{path}", headers=auth_headers("priya"), **kwargs).status_code == 403


def test_admin_analyzes_the_sample(cost_client, auth_headers):
    admin = auth_headers("admin")
    sample = cost_client.get(f"{URL}/sample", headers=admin)
    assert sample.status_code == 200
    assert sample.headers["content-type"].startswith("text/csv")

    response = upload(cost_client, admin, sample.content, standard_price="20", premium_price="30")
    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["seats_purchased"] == 20
    assert metrics["unused_seats"] == 4
    assert metrics["potential_monthly_saving"] == 230.0


def test_default_prices_apply(cost_client, auth_headers):
    sample = cost_client.get(f"{URL}/sample", headers=auth_headers("admin")).content
    response = upload(cost_client, auth_headers("admin"), sample)
    assert response.json()["metrics"]["potential_monthly_saving"] == 230.0


def test_bad_csv_returns_clear_400(cost_client, auth_headers):
    response = upload(cost_client, auth_headers("admin"), b"user_name,department\nA,B\n")
    assert response.status_code == 400
    assert "Missing columns" in response.json()["detail"]


def test_bad_price_returns_400(cost_client, auth_headers):
    response = upload(cost_client, auth_headers("admin"), HEADER + ",,standard,,,\n",
                      standard_price="40", premium_price="30")
    assert response.status_code == 400
    assert "premium price" in response.json()["detail"]