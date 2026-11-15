"""FastAPI backend: serves the catalog, cached time series, and trend analysis."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .stats import analyze

BASE = Path(__file__).parent
CATALOG = BASE / "catalog"

app = FastAPI(title="Earth System Trend Detective API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", BASE.parent / "data"))


@lru_cache
def _catalog():
    variables = json.loads((CATALOG / "variables.json").read_text())["variables"]
    regions = json.loads((CATALOG / "regions.json").read_text())["regions"]
    return variables, {r["id"]: r for r in regions}


@lru_cache(maxsize=256)
def _load(path: str, mtime: float) -> pd.Series:
    df = pd.read_parquet(path)
    return pd.Series(df["value"].to_numpy(), index=pd.DatetimeIndex(df["date"]), name="value")


def _series(region_id: str, var_id: str) -> pd.Series:
    if not _is_cached(region_id, var_id):
        raise HTTPException(404, f"No cached data for {var_id} in {region_id}.")
    p = data_dir() / f"{region_id}__{var_id}.parquet"
    return _load(str(p), p.stat().st_mtime)


MIN_MONTHS = 36  # matches the minimum the statistics engine accepts


def _is_cached(region_id: str, var_id: str) -> bool:
    """True when a usable cache file exists. Partial files (an interrupted download) are
    ignored, so the app never offers a variable that would fail to analyze."""
    p = data_dir() / f"{region_id}__{var_id}.parquet"
    if not p.exists():
        return False
    try:
        return pq.ParquetFile(p).metadata.num_rows >= MIN_MONTHS
    except Exception:
        return False


def _validate(region_id: str, var_id: str):
    variables, regions = _catalog()
    if region_id not in regions:
        raise HTTPException(404, f"Unknown region '{region_id}'.")
    if var_id not in variables:
        raise HTTPException(404, f"Unknown variable '{var_id}'.")
    return variables[var_id], regions[region_id]


def _run(region_id: str, var_id: str, start: str | None, end: str | None, alpha: float) -> dict:
    var, region = _validate(region_id, var_id)
    s = _series(region_id, var_id)
    if start:
        s = s[s.index >= pd.Timestamp(start)]
    if end:
        s = s[s.index <= pd.Timestamp(end)]
    try:
        result = analyze(s.index, s.to_numpy(), var["display_unit"], alpha)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    result["region"] = {"id": region_id, "name": region["name"], "bbox": region["bbox"]}
    result["variable"] = {"id": var_id, "label": var["label"], "source": var["source"],
                          "unit": var["display_unit"], "definition": var["definition"],
                          "why_it_matters": var["why_it_matters"]}
    return result


def _standardize(result: dict) -> dict:
    """Add a unit-free series (anomalies divided by their std) so different variables
    can share one axis in a comparison chart."""
    a = pd.Series(result["series"]["anomalies"])
    std = float(a.std()) or 1.0
    result["series"]["anomalies_z"] = (a / std).round(4).tolist()
    return result


@app.get("/")
def root():
    return {
        "name": "Earth System Trend Detective API",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": ["/api/regions", "/api/variables", "/api/analyze",
                      "/api/compare/regions", "/api/compare/variables"],
    }


@app.get("/api/health")
def health():
    meta = data_dir() / "_meta.json"
    return {"status": "ok", "data": json.loads(meta.read_text()) if meta.exists() else {"synthetic": False}}


@app.get("/api/variables")
def variables():
    return _catalog()[0]


@app.get("/api/regions")
def regions():
    variables, regs = _catalog()
    out = []
    for r in regs.values():
        avail = [v for v in r["variables"] if _is_cached(r["id"], v)]
        out.append({**r, "variables": avail,
                    "default_variables": [v for v in r["default_variables"] if v in avail]})
    return out


@app.get("/api/analyze")
def analyze_one(region: str, variable: str, start: str | None = None, end: str | None = None,
                alpha: float = Query(0.05, gt=0, lt=0.5)):
    return _run(region, variable, start, end, alpha)


@app.get("/api/compare/regions")
def compare_regions(variable: str, regions: str, start: str | None = None, end: str | None = None,
                    alpha: float = Query(0.05, gt=0, lt=0.5)):
    """Same variable in several regions. Example: ?variable=T2M&regions=sahel,amazon_arc"""
    ids = [r for r in regions.split(",") if r]
    if len(ids) < 2:
        raise HTTPException(422, "Give at least two regions.")
    results = [_standardize(_run(r, variable, start, end, alpha)) for r in ids]
    opposite = (len({x["sen"]["per_decade"] > 0 for x in results if x["mann_kendall"]["significant"]}) > 1)
    return {"variable": variable, "results": results,
            "opposite_significant_trends": opposite}


@app.get("/api/compare/variables")
def compare_variables(region: str, variables: str, start: str | None = None, end: str | None = None,
                      alpha: float = Query(0.05, gt=0, lt=0.5)):
    """Several variables in one region. Example: ?region=sahel&variables=PRECTOT,NDVI"""
    ids = [v for v in variables.split(",") if v]
    if len(ids) < 2:
        raise HTTPException(422, "Give at least two variables.")
    results = [_standardize(_run(region, v, start, end, alpha)) for v in ids]
    # Correlation of deseasonalised anomalies on the shared months (a hint, not proof, of linkage).
    corr = {}
    frames = {x["variable"]["id"]: pd.Series(x["series"]["anomalies"], index=x["series"]["dates"])
              for x in results}
    df = pd.DataFrame(frames).dropna()
    if len(df) >= 24:
        c = df.corr()
        corr = {a: {b: round(float(c.loc[a, b]), 3) for b in c.columns} for a in c.index}
    return {"region": region, "results": results, "anomaly_correlation": corr}