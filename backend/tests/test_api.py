import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.synthetic import make_cache


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import os
    d = tmp_path_factory.mktemp("cache")
    make_cache(d)
    os.environ["DATA_DIR"] = str(d)
    from app.main import app
    yield TestClient(app)
    os.environ.pop("DATA_DIR")


def test_health_flags_synthetic(client):
    assert client.get("/api/health").json()["data"]["synthetic"] is True


def test_regions_and_variables(client):
    regions = client.get("/api/regions").json()
    assert len(regions) == 7 and all(r["bbox"] and r["variables"] for r in regions)
    assert "T2M" in client.get("/api/variables").json()


def test_analyze(client):
    r = client.get("/api/analyze", params={"region": "sahel", "variable": "T2M"}).json()
    assert r["verdict"]["text"] and r["sen"]["per_decade_ci"][0] < r["sen"]["per_decade_ci"][1]
    assert len(r["series"]["dates"]) == len(r["series"]["trend_line"])
    assert r["variable"]["definition"]


def test_date_window(client):
    r = client.get("/api/analyze", params={"region": "sahel", "variable": "T2M",
                                           "start": "2010-01-01", "end": "2020-12-31"}).json()
    assert r["start"] >= "2010-01-01" and r["end"] <= "2020-12-31"


def test_window_too_short_is_422(client):
    r = client.get("/api/analyze", params={"region": "sahel", "variable": "T2M",
                                           "start": "2020-01-01", "end": "2021-06-01"})
    assert r.status_code == 422


def test_unknown_region_and_uncached_variable(client):
    assert client.get("/api/analyze", params={"region": "nope", "variable": "T2M"}).status_code == 404
    assert client.get("/api/analyze", params={"region": "arctic_barents", "variable": "NDVI"}).status_code == 404


def test_compare_regions(client):
    r = client.get("/api/compare/regions", params={"variable": "T2M", "regions": "sahel,aral_sea"}).json()
    assert len(r["results"]) == 2 and "anomalies_z" in r["results"][0]["series"]
    assert isinstance(r["opposite_significant_trends"], bool)


def test_compare_variables(client):
    r = client.get("/api/compare/variables", params={"region": "sahel", "variables": "T2M,PRECTOT"}).json()
    assert r["anomaly_correlation"]["T2M"]["T2M"] == 1.0


def test_partial_cache_files_are_not_offered(tmp_path, monkeypatch):
    make_cache(tmp_path)
    p = tmp_path / "sahel__T2M.parquet"
    pd.read_parquet(p).head(10).to_parquet(p, index=False)  # simulate an interrupted download
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app
    c = TestClient(app)
    sahel = next(r for r in c.get("/api/regions").json() if r["id"] == "sahel")
    assert "T2M" not in sahel["variables"] and "PRECTOT" in sahel["variables"]
    assert c.get("/api/analyze", params={"region": "sahel", "variable": "T2M"}).status_code == 404


def test_root_points_to_the_docs(client):
    r = client.get("/")
    assert r.status_code == 200 and r.json()["docs"] == "/docs"