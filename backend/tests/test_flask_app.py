"""The Flask API must behave like the FastAPI one (same endpoints, same JSON, same errors)."""
import pytest

from app.synthetic import make_cache


@pytest.fixture(scope="module")
def client(tmp_path_factory, monkeypatch_module=None):
    import os
    d = tmp_path_factory.mktemp("flask_cache")
    make_cache(d)
    os.environ["DATA_DIR"] = str(d)
    import flask_app
    yield flask_app.app.test_client()
    os.environ.pop("DATA_DIR")


def test_matches_fastapi_output(client):
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app
    f = TestClient(fastapi_app)
    for url in ["/api/analyze?region=sahel&variable=T2M&start=2005-01-01",
                "/api/compare/regions?variable=T2M&regions=sahel,aral_sea",
                "/api/compare/variables?region=sahel&variables=T2M,PRECTOT",
                "/api/regions", "/api/variables", "/api/health"]:
        assert client.get(url).get_json() == f.get(url).json(), url


def test_errors(client):
    assert client.get("/api/analyze?region=nope&variable=T2M").status_code == 404
    assert client.get("/api/analyze?region=arctic_barents&variable=NDVI").status_code == 404
    assert client.get("/api/analyze?region=sahel&variable=T2M&start=2020-01-01&end=2021-06-01").status_code == 422
    assert client.get("/api/analyze?region=sahel&variable=T2M&alpha=0.9").status_code == 422
    assert client.get("/api/analyze?region=sahel").status_code == 422
    assert client.get("/api/compare/regions?variable=T2M&regions=sahel").status_code == 422
    assert client.get("/api/analyze?region=sahel&variable=T2M&start=garbage").status_code == 422


def test_cors_and_root(client):
    r = client.get("/", headers={"Origin": "https://x.netlify.app"})
    assert r.headers["Access-Control-Allow-Origin"] == "*"
    assert r.get_json()["docs"] == "/docs"
