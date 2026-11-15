"""Audit the cache: coverage, gaps, NaNs, plausible value ranges, and two cross-checks.

    python scripts/check_cache.py                       # checks backend/data
    python scripts/check_cache.py data_synthetic        # or another folder

Prints one line per (region, variable) and a list of PROBLEMS at the end.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "data")
CATALOG = ROOT / "app" / "catalog"

# Plausible monthly area-mean ranges, in display units. Outside these, a unit or subsetting bug is likely.
RANGE = {
    "T2M": (-60, 50), "LST": (-60, 80), "PRECIP": (0, 40), "PRECTOT": (0, 40), "AOD": (0, 3),
    "SOILM": (0, 80), "EVAP": (-1, 15), "NDVI": (-0.2, 1.0),
}
MIN_MONTHS = 36

variables = json.loads((CATALOG / "variables.json").read_text())["variables"]
regions = json.loads((CATALOG / "regions.json").read_text())["regions"]
problems: list[str] = []
series: dict[tuple[str, str], pd.Series] = {}

print(f"{'region':16s} {'var':8s} {'rows':>5s}  {'first':7s} {'last':7s} {'min':>9s} {'mean':>9s} {'max':>9s}")
for r in regions:
    for v in r["variables"]:
        p = DATA / f"{r['id']}__{v}.parquet"
        tag = f"{r['id']}/{v}"
        if not p.exists():
            print(f"{r['id']:16s} {v:8s}  missing")
            if v in ("T2M", "PRECTOT", "AOD", "SOILM", "EVAP", "PRECIP"):
                problems.append(f"{tag}: file missing")
            continue
        d = pd.read_parquet(p)
        s = pd.Series(d["value"].to_numpy(), index=pd.DatetimeIndex(d["date"])).sort_index()
        series[(r["id"], v)] = s
        print(f"{r['id']:16s} {v:8s} {len(s):5d}  {s.index[0]:%Y-%m} {s.index[-1]:%Y-%m} "
              f"{s.min():9.3f} {s.mean():9.3f} {s.max():9.3f}")

        full = pd.date_range(s.index[0], s.index[-1], freq="MS")
        missing = full.difference(s.index)
        if len(s) < MIN_MONTHS:
            problems.append(f"{tag}: only {len(s)} months (needs {MIN_MONTHS})")
        if len(missing):
            problems.append(f"{tag}: {len(missing)} missing months, first {missing[0]:%Y-%m}")
        if s.index.has_duplicates:
            problems.append(f"{tag}: duplicate months")
        if s.isna().any():
            problems.append(f"{tag}: {int(s.isna().sum())} NaN values")
        if s.std() == 0:
            problems.append(f"{tag}: constant series")
        lo, hi = RANGE.get(v, (-np.inf, np.inf))
        if s.min() < lo or s.max() > hi:
            problems.append(f"{tag}: values outside plausible range {lo} to {hi} ({s.min():.2f} to {s.max():.2f})")
        start = pd.Timestamp(f"{variables[v]['start_year']}-01-01")
        if s.index[0] > start + pd.DateOffset(months=6):  # GPM IMERG starts mid-2000, MODIS early 2000
            problems.append(f"{tag}: starts {s.index[0]:%Y-%m}, expected about {start:%Y-%m}")

print("\nCross-checks")
# 1. Two independent precipitation sources should agree in size and timing.
for r in regions:
    a, b = series.get((r["id"], "PRECIP")), series.get((r["id"], "PRECTOT"))
    if a is None or b is None:
        continue
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    corr = j.iloc[:, 0].corr(j.iloc[:, 1])
    ratio = j.iloc[:, 0].mean() / j.iloc[:, 1].mean() if j.iloc[:, 1].mean() else np.nan
    print(f"  GPM vs MERRA-2 precipitation, {r['id']:16s} r = {corr:5.2f}   mean ratio = {ratio:5.2f}")
    if not corr > 0.5:
        problems.append(f"{r['id']}: GPM and MERRA-2 precipitation barely correlate (r = {corr:.2f})")
    if not 0.3 < ratio < 3:
        problems.append(f"{r['id']}: GPM/MERRA-2 precipitation mean ratio {ratio:.2f} (unit problem?)")

# 2. The Arctic should be much colder than the tropics.
t = {rid: s.mean() for (rid, v), s in series.items() if v == "T2M"}
if "arctic_barents" in t and "sahel" in t:
    print(f"  Mean air temperature: Arctic {t['arctic_barents']:.1f} C, Sahel {t['sahel']:.1f} C")
    if not t["arctic_barents"] < t["sahel"] - 15:
        problems.append("Arctic is not much colder than the Sahel: check the T2M subsetting")

print("\nPROBLEMS" if problems else "\nNo problems found.")
for p in problems:
    print("  -", p)
sys.exit(1 if problems else 0)