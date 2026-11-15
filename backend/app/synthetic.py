"""FAKE data generator for developing the frontend before the real cache exists.

Every number produced here is invented. The generator writes `_meta.json` with
{"synthetic": true} so /api/health tells the frontend to show a warning banner.
Never deploy this data as if it were real.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# (typical mean, seasonal amplitude, noise sd, trend per decade) in display units
BASE = {
    "T2M": (15, 10, 0.8, 0.3), "PRECIP": (2, 1.5, 0.5, 0.0), "PRECTOT": (2, 1.5, 0.5, 0.0),
    "AOD": (0.3, 0.1, 0.05, 0.0), "SOILM": (25, 5, 2, 0.0), "EVAP": (1.5, 1.0, 0.3, 0.0),
    "NDVI": (0.5, 0.15, 0.03, 0.0), "LST": (28, 12, 1.2, 0.4),
}


def make_cache(out_dir: Path, end: str = "2025-12", seed: int = 0) -> None:
    root = Path(__file__).parent / "catalog"
    variables = json.loads((root / "variables.json").read_text())["variables"]
    regions = json.loads((root / "regions.json").read_text())["regions"]
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    for r in regions:
        for v in r["variables"]:
            mean, amp, sd, _ = BASE[v]
            idx = pd.date_range(f"{variables[v]['start_year']}-01-01", end, freq="MS")
            t = np.arange(len(idx)) / 12
            trend = rng.choice([-1, 0, 1]) * rng.uniform(0.2, 1.0) * sd * 2  # per decade, invented
            e = np.zeros(len(idx))
            eps = rng.normal(0, sd, len(idx))
            for k in range(1, len(idx)):
                e[k] = 0.5 * e[k - 1] + eps[k]
            y = mean + amp * np.sin(2 * np.pi * t) + trend / 10 * t + e
            pd.DataFrame({"date": idx, "value": y}).to_parquet(out_dir / f"{r['id']}__{v}.parquet", index=False)
    (out_dir / "_meta.json").write_text(json.dumps({"synthetic": True}))