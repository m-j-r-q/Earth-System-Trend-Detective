"""Offline tests for scripts/build_cache.py using fake granules (no network)."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("earthaccess")
pytest.importorskip("xarray")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_cache", ROOT / "scripts" / "build_cache.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

MONTHS = pd.date_range("2000-01-01", "2003-12-01", freq="MS")


def fake_granule(month):
    return {
        "umm": {"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": month.strftime("%Y-%m-%dT00:00:00.000Z")}},
                "RelatedUrls": []},
        "meta": {"concept-id": f"G-{month:%Y%m}"},
    }


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(bc, "DATA", tmp_path)
    monkeypatch.setattr(bc, "RETRIES", 1)
    monkeypatch.setattr(bc.earthaccess, "search_data", lambda **kw: [fake_granule(m) for m in MONTHS])
    calls = []

    def fake_read(g, short_name, needed, variables, method):
        m = bc.granule_month(g)
        calls.append(m)
        return {(r["id"], v): float(m.month) for v, rs in needed.items() for r in rs}

    monkeypatch.setattr(bc, "read_granule", fake_read)
    variables, regions = bc.load_catalog()
    run = lambda: bc.process_product("M2TMNXSLV", ["T2M"], variables, regions, "2003-12", "opendap", 4)
    return tmp_path, calls, run


def test_builds_one_file_per_region(env):
    tmp, calls, run = env
    run()
    files = sorted(p.name for p in tmp.glob("*__T2M.parquet"))
    assert len(files) == 7
    df = pd.read_parquet(tmp / "sahel__T2M.parquet")
    assert len(df) == 48 and df["date"].is_monotonic_increasing and df["date"].is_unique


def test_rerun_fetches_nothing(env):
    tmp, calls, run = env
    run()
    calls.clear()
    run()
    assert calls == []


def test_resume_fetches_only_missing_months(env):
    tmp, calls, run = env
    run()
    p = tmp / "sahel__T2M.parquet"
    df = pd.read_parquet(p)
    gaps = set(df["date"].iloc[[3, 10, 11, 30, 47]])
    df[~df["date"].isin(gaps)].to_parquet(p, index=False)  # simulate an interrupted run
    calls.clear()
    run()
    assert set(calls) == gaps
    assert len(pd.read_parquet(p)) == 48


def test_checkpoints_are_written(env, monkeypatch):
    tmp, calls, run = env
    monkeypatch.setattr(bc, "CHECKPOINT_EVERY", 10)
    saves = []
    real = bc.save
    monkeypatch.setattr(bc, "save", lambda rows: (saves.append(1), real(rows))[1])
    run()
    assert len(saves) >= 5  # 4 mid-run checkpoints + the final save


def test_fails_fast_when_everything_fails(env, monkeypatch):
    tmp, calls, run = env

    def boom(*a, **k):
        raise RuntimeError("Forbidden")

    monkeypatch.setattr(bc, "read_granule", boom)
    with pytest.raises(SystemExit) as e:
        run()
    assert "all failed" in str(e.value)
    assert not list(tmp.glob("*.parquet"))


def test_error_text_never_contains_headers():
    class E(Exception):
        status = 403

    msg = bc.describe(E("Forbidden\nAuthorization: Bearer SECRET"))
    assert "SECRET" not in msg and "status=403" in msg


def test_auto_falls_back_to_streaming_and_stops_trying_opendap(monkeypatch):
    bc.reset_method_state()
    calls = {"opendap": 0, "stream": 0}

    def bad_opendap(*a, **k):
        calls["opendap"] += 1
        raise ValueError("dimensions mismatch")

    def good_stream(*a, **k):
        calls["stream"] += 1
        return {("sahel", "T2M"): 1.0}

    monkeypatch.setattr(bc, "_read_opendap", bad_opendap)
    monkeypatch.setattr(bc, "_read_stream", good_stream)
    for _ in range(8):
        assert bc.read_granule({}, "GLDAS_NOAH025_M", {}, {}, "auto") == {("sahel", "T2M"): 1.0}
    assert calls["stream"] == 8
    assert calls["opendap"] == bc.OPENDAP_GIVE_UP_AFTER  # gave up after the allowed failures


def test_auto_keeps_using_opendap_when_it_works(monkeypatch):
    bc.reset_method_state()
    monkeypatch.setattr(bc, "_read_opendap", lambda *a, **k: {"x": 1})
    monkeypatch.setattr(bc, "_read_stream", lambda *a, **k: pytest.fail("should not stream"))
    for _ in range(6):
        assert bc.read_granule({}, "M2TMNXSLV", {}, {}, "auto") == {"x": 1}


def test_explicit_opendap_does_not_fall_back(monkeypatch):
    bc.reset_method_state()
    monkeypatch.setattr(bc, "_read_opendap", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))
    monkeypatch.setattr(bc, "_read_stream", lambda *a, **k: pytest.fail("should not stream"))
    with pytest.raises(ValueError):
        bc.read_granule({}, "M2TMNXSLV", {}, {}, "opendap")


class _Resp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


class _Session:
    def __init__(self, content):
        self.content = content
        self.urls = []

    def get(self, url, **kw):
        self.urls.append(url)
        return _Resp(self.content)


def _netcdf_bytes(tmp_path, value, dims, group=None, name="T2M"):
    import numpy as np
    import xarray as xr

    lat = np.arange(-89.5, 90, 1.0)
    lon = np.arange(-179.5, 180, 1.0)
    shape = {"time": 1, "lat": lat.size, "lon": lon.size}
    da = xr.DataArray(np.full([shape[d] for d in dims], value), dims=dims,
                      coords={"lat": lat, "lon": lon}, name=name)
    path = tmp_path / "f.nc"
    da.to_dataset().to_netcdf(path, engine="h5netcdf", group=group)
    return path.read_bytes()


GRANULE = {"umm": {"RelatedUrls": [
    {"Type": "GET DATA VIA DIRECT ACCESS", "URL": "s3://bucket/x.nc4"},
    {"Type": "VIEW RELATED INFORMATION", "URL": "https://data.example.gov/s3credentials"},
    {"Type": "GET DATA", "URL": "https://data.example.gov/data/x.nc4"},
]}}
NEEDED = {"V": [{"id": "sahel", "bbox": [-15, 10, 20, 17]}]}


def test_data_url_picks_the_https_download_link():
    assert bc.data_url(GRANULE) == "https://data.example.gov/data/x.nc4"
    with pytest.raises(LookupError):
        bc.data_url({"umm": {"RelatedUrls": [{"Type": "GET DATA VIA DIRECT ACCESS", "URL": "s3://b/x"}]}})


def test_stream_reads_regions_from_downloaded_bytes(tmp_path, monkeypatch):
    pytest.importorskip("h5netcdf")
    session = _Session(_netcdf_bytes(tmp_path, 300.0, ("time", "lat", "lon")))
    monkeypatch.setattr(bc, "thread_session", lambda: session)
    variables = {"V": {"field": "T2M", "scale": 1, "offset": -273.15}}
    out = bc._read_stream(GRANULE, "M2TMNXSLV", NEEDED, variables)
    assert out[("sahel", "V")] == pytest.approx(26.85)
    assert session.urls == ["https://data.example.gov/data/x.nc4"]  # one download per granule


def test_stream_reads_gpm_style_group_and_dimension_order(tmp_path, monkeypatch):
    pytest.importorskip("h5netcdf")
    blob = _netcdf_bytes(tmp_path, 1.0, ("time", "lon", "lat"), group="Grid", name="precipitation")
    monkeypatch.setattr(bc, "thread_session", lambda: _Session(blob))
    variables = {"V": {"field": "precipitation", "scale": 24, "offset": 0}}
    out = bc._read_stream(GRANULE, "GPM_3IMERGM", NEEDED, variables)
    assert out[("sahel", "V")] == pytest.approx(24.0)