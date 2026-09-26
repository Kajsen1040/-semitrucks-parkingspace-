from unittest.mock import Mock, patch
from pathlib import Path

from app import app


def test_search_validates_coordinates():
    client = app.test_client()
    response = client.post("/api/search", json={"lat": 91, "lng": 18, "radius": 10000})
    assert response.status_code == 400
    assert "lat" in response.json["error"]

    nan_response = client.post("/api/search", json={"lat": "nan", "lng": 18, "radius": 10000})
    assert nan_response.status_code == 400
    assert "ändligt" in nan_response.json["error"]


def test_search_does_not_accept_coordinates_in_get_url():
    response = app.test_client().get("/api/search?lat=59.3&lng=18.1&radius=10000")

    assert response.status_code == 405


def test_responses_prevent_location_caching():
    response = app.test_client().get("/")

    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_missing_dataset_does_not_call_overpass_by_default(monkeypatch):
    monkeypatch.setattr("app.DATA_PATH", Path("missing-test-dataset.json"))
    with patch("app.requests.post") as post:
        response = app.test_client().post(
            "/api/search", json={"lat": 59.3, "lng": 18.1, "radius": 10000}
        )

    assert response.status_code == 200
    assert response.json["places"] == []
    post.assert_not_called()


def test_oversized_request_is_rejected_without_request_data():
    response = app.test_client().post(
        "/api/search",
        json={"lat": 59.3, "lng": 18.1, "radius": 10000, "unused": "x" * 5000},
    )

    assert response.status_code == 413
    assert response.json["error"] == "Förfrågan är för stor."


def test_search_accepts_150_km_but_rejects_larger_radius(monkeypatch):
    response_mock = Mock()
    response_mock.raise_for_status.return_value = None
    response_mock.json.return_value = {"elements": []}
    with patch("app.requests.post", return_value=response_mock):
        client = app.test_client()
        accepted = client.post("/api/search", json={"lat": 59.3, "lng": 18.1, "radius": 150000})
        rejected = client.post("/api/search", json={"lat": 59.3, "lng": 18.1, "radius": 150001})

    assert accepted.status_code == 200
    assert rejected.status_code == 400
    assert "150 000" in rejected.json["error"]


def test_search_returns_normalized_places(monkeypatch):
    monkeypatch.setattr("app.DATA_PATH", Path("missing-test-dataset.json"))
    monkeypatch.setattr("app.ALLOW_LIVE_FALLBACK", True)
    overpass_response = Mock()
    overpass_response.raise_for_status.return_value = None
    overpass_response.json.return_value = {
        "elements": [{
            "type": "node",
            "id": 123,
            "lat": 59.3,
            "lon": 18.1,
            "tags": {"name": "Rastplats", "hgv": "designated"},
        }]
    }
    with patch("app.requests.post", return_value=overpass_response) as post:
        response = app.test_client().post("/api/search", json={"lat": 59.3, "lng": 18.1, "radius": 10000})

    assert response.status_code == 200
    assert response.json["places"][0]["name"] == "Rastplats"
    assert response.json["places"][0]["truckRelevant"] is True
    post.assert_called_once()
