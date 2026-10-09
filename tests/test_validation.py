from conftest import register


def test_malformed_geojson_returns_422(client):
    register(client)
    response = client.post(
        "/api/v1/territories",
        json={
            "name": "Плохой полигон",
            "latitude": 43.2,
            "longitude": 76.9,
            "area": 10,
            "timezone": "Asia/Almaty",
            "polygon": {"type": "Polygon", "coordinates": [1]},
        },
    )
    assert response.status_code == 422


def test_browser_mutation_requires_csrf_header_and_expected_origin(client):
    register(client)
    missing_header = client.post(
        "/api/v1/territories",
        headers={"Origin": "http://localhost:5173", "X-GAIA-Request": ""},
        json={"name": "Двор", "latitude": 43.2, "longitude": 76.9, "area": 10},
    )
    assert missing_header.status_code == 403
    bad_origin = client.post(
        "/api/v1/territories",
        headers={"Origin": "https://attacker.example"},
        json={"name": "Двор", "latitude": 43.2, "longitude": 76.9, "area": 10},
    )
    assert bad_origin.status_code == 403
