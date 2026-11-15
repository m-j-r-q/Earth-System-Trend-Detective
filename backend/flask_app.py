"""Flask version of the API, for PythonAnywhere.

PythonAnywhere runs apps inside uWSGI "multiple interpreter" mode, where FastAPI's compiled
dependency (pydantic) hangs. This file serves the same endpoints and the same JSON with plain Flask,
reusing app/stats.py unchanged. Run locally with:  DATA_DIR=data flask --app flask_app run
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

from app.stats import analyze

BASE = Path(__file__).parent / "app"
CATALOG = BASE / "catalog"
MIN_MONTHS = 36

app = Flask(__name__)
app.json.sort_keys = False


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        self.status, self.detail = status, detail


@app.errorhandler(ApiError)
def _api_error(e):
    return jsonify({"detail": e.detail}), e.status


@app.after_request
def _cors(resp):
    allowed = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]
    origin = request.headers.get("Origin")
    if "*" in allowed:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in allowed:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    return resp


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))


@lru_cache
def _catalog():
    variables = json.loads((CATALOG / "variables.json").read_text())["variables"]
    regions = json.loads((CATALOG / "regions.json").read_text())["regions"]
    return variables, {r["id"]: r for r in regions}


def _cache_file(region_id: str, var_id: str):
    for ext in ("csv", "parquet"):  # CSV first: needs no pyarrow
        p = data_dir() / f"{region_id}__{var_id}.{ext}"
        if p.exists():
            return p
    return None


@lru_cache(maxsize=256)
def _load(path: str, mtime: float) -> pd.Series:
    df = pd.read_csv(path, parse_dates=["date"]) if path.endswith(".csv") else pd.read_parquet(path)
    return pd.Series(df["value"].to_numpy(), index=pd.DatetimeIndex(df["date"]), name="value")


def _is_cached(region_id: str, var_id: str) -> bool:
    p = _cache_file(region_id, var_id)
    if p is None:
        return False
    try:
        if p.suffix == ".csv":
            with open(p) as f:
                return sum(1 for _ in f) - 1 >= MIN_MONTHS
        import pyarrow.parquet as pq
        return pq.ParquetFile(p).metadata.num_rows >= MIN_MONTHS
    except Exception:
        return False


def _series(region_id: str, var_id: str) -> pd.Series:
    if not _is_cached(region_id, var_id):
        raise ApiError(404, f"No cached data for {var_id} in {region_id}.")
    p = _cache_file(region_id, var_id)
    return _load(str(p), p.stat().st_mtime)


def _alpha() -> float:
    try:
        a = float(request.args.get("alpha", 0.05))
    except ValueError:
        raise ApiError(422, "alpha must be a number.")
    if not 0 < a < 0.5:
        raise ApiError(422, "alpha must be between 0 and 0.5.")
    return a


def _run(region_id: str, var_id: str, start, end, alpha: float) -> dict:
    variables, regions = _catalog()
    if region_id not in regions:
        raise ApiError(404, f"Unknown region '{region_id}'.")
    if var_id not in variables:
        raise ApiError(404, f"Unknown variable '{var_id}'.")
    var, region = variables[var_id], regions[region_id]
    s = _series(region_id, var_id)
    try:
        if start:
            s = s[s.index >= pd.Timestamp(start)]
        if end:
            s = s[s.index <= pd.Timestamp(end)]
    except (ValueError, TypeError):
        raise ApiError(422, "start and end must be dates like 2010-01-01.")
    try:
        result = analyze(s.index, s.to_numpy(), var["display_unit"], alpha)
    except ValueError as exc:
        raise ApiError(422, str(exc))
    result["region"] = {"id": region_id, "name": region["name"], "bbox": region["bbox"]}
    result["variable"] = {"id": var_id, "label": var["label"], "source": var["source"],
                          "unit": var["display_unit"], "definition": var["definition"],
                          "why_it_matters": var["why_it_matters"]}
    return result


def _standardize(result: dict) -> dict:
    a = pd.Series(result["series"]["anomalies"])
    std = float(a.std()) or 1.0
    result["series"]["anomalies_z"] = (a / std).round(4).tolist()
    return result


def _need(name: str) -> str:
    v = request.args.get(name)
    if not v:
        raise ApiError(422, f"Missing query parameter '{name}'.")
    return v


@app.get("/")
def root():
    return jsonify({
        "name": "Earth System Trend Detective API", "docs": "/docs", "health": "/api/health",
        "endpoints": ["/api/regions", "/api/variables", "/api/analyze",
                      "/api/compare/regions", "/api/compare/variables"],
    })


@app.get("/api/health")
def health():
    meta = data_dir() / "_meta.json"
    return jsonify({"status": "ok", "data": json.loads(meta.read_text()) if meta.exists() else {"synthetic": False}})


@app.get("/api/variables")
def variables():
    return jsonify(_catalog()[0])


@app.get("/api/regions")
def regions():
    _, regs = _catalog()
    out = []
    for r in regs.values():
        avail = [v for v in r["variables"] if _is_cached(r["id"], v)]
        out.append({**r, "variables": avail,
                    "default_variables": [v for v in r["default_variables"] if v in avail]})
    return jsonify(out)


@app.get("/api/analyze")
def analyze_one():
    return jsonify(_run(_need("region"), _need("variable"), request.args.get("start"),
                        request.args.get("end"), _alpha()))


@app.get("/api/compare/regions")
def compare_regions():
    variable = _need("variable")
    ids = [r for r in _need("regions").split(",") if r]
    if len(ids) < 2:
        raise ApiError(422, "Give at least two regions.")
    a = _alpha()
    results = [_standardize(_run(r, variable, request.args.get("start"), request.args.get("end"), a)) for r in ids]
    opposite = len({x["sen"]["per_decade"] > 0 for x in results if x["mann_kendall"]["significant"]}) > 1
    return jsonify({"variable": variable, "results": results, "opposite_significant_trends": opposite})


@app.get("/api/compare/variables")
def compare_variables():
    region = _need("region")
    ids = [v for v in _need("variables").split(",") if v]
    if len(ids) < 2:
        raise ApiError(422, "Give at least two variables.")
    a = _alpha()
    results = [_standardize(_run(region, v, request.args.get("start"), request.args.get("end"), a)) for v in ids]
    corr = {}
    frames = {x["variable"]["id"]: pd.Series(x["series"]["anomalies"], index=x["series"]["dates"])
              for x in results}
    df = pd.DataFrame(frames).dropna()
    if len(df) >= 24:
        c = df.corr()
        corr = {p: {q: round(float(c.loc[p, q]), 3) for q in c.columns} for p in c.index}
    return jsonify({"region": region, "results": results, "anomaly_correlation": corr})
