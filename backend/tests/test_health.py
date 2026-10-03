from fastapi.testclient import TestClient

from sentinel.main import app

client = TestClient(app)


def test_health_mengembalikan_status_ok_dan_versi():
    respons = client.get("/health")

    assert respons.status_code == 200
    assert respons.json() == {"status": "ok", "versi": "0.1.0"}
