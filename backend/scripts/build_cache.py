"""Build the local data cache: one monthly area-mean time series per (region, variable).

Run this on YOUR machine (needs your NASA Earthdata login):

    pip install -r requirements-cache.txt pydap
    python scripts/build_cache.py --vars T2M          # smoke test first
    python scripts/build_cache.py                     # everything
    python scripts/build_cache.py --workers 16        # more parallelism
    python scripts/build_cache.py --vars PRECIP --method stream   # fallback access method

Access method (default "auto"): OPeNDAP first, where NASA's server cuts out only the requested
box (benchmarked about 4x faster than streaming whole files, with identical values). If OPeNDAP
fails for a product, e.g. GLDAS, it streams the files instead. Granules are
processed in parallel threads (the cost is network waiting, not CPU).

The script resumes: it only fetches months that are missing, and it saves a checkpoint
every 100 granules, so Ctrl+C or a crash loses very little.

Covers the NetCDF/HDF5 products (MERRA-2, GPM IMERG, GLDAS). MODIS NDVI and LST are
HDF4 and are imported separately.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import earthaccess
import numpy as np
import pandas as pd
import xarray as xr

warnings.filterwarnings("ignore", message="PyDAP was unable to determine the DAP protocol")

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app" / "catalog"
DATA = ROOT / "data"

VERSIONS = {
    "M2TMNXSLV": "5.12.4",
    "M2TMNXFLX": "5.12.4",
    "M2TMNXAER": "5.12.4",
    "GPM_3IMERGM": "07",
    "GLDAS_NOAH025_M": "2.1",
}
# NetCDF/HDF5 group holding the data (GPM IMERG stores everything under /Grid).
GROUPS = {"GPM_3IMERGM": "Grid"}

RETRIES = 3
CHECKPOINT_EVERY = 100
FAIL_FAST_AFTER = 6  # if this many granules finish and none succeeded, stop


def describe(exc: Exception) -> str:
    """Short error text. Never print repr(exc): HTTP errors include request headers,
    and those contain your Earthdata bearer token."""
    return f"{type(exc).__name__} status={getattr(exc, 'status', None)}: {str(exc)[:100].splitlines()[0]}"


def load_catalog():
    variables = json.loads((CATALOG / "variables.json").read_text())["variables"]
    regions = json.loads((CATALOG / "regions.json").read_text())["regions"]
    return variables, regions


def cache_path(region_id: str, var_id: str) -> Path:
    return DATA / f"{region_id}__{var_id}.parquet"


def cached_months(region_ids, var_id) -> set:
    """Months present in ALL region files of this variable."""
    sets = []
    for rid in region_ids:
        p = cache_path(rid, var_id)
        if not p.exists():
            return set()
        sets.append(set(pd.read_parquet(p)["date"]))
    return set.intersection(*sets) if sets else set()


def month_start(t) -> pd.Timestamp:
    return pd.Timestamp(pd.to_datetime(str(t)[:10])).to_period("M").to_timestamp()


def granule_month(granule) -> pd.Timestamp:
    return month_start(granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"])


def area_mean(da: xr.DataArray, bbox) -> float:
    w, s, e, n = bbox
    sub = da.sel(lat=slice(s, n), lon=slice(w, e))
    weights = np.cos(np.deg2rad(sub["lat"]))
    return float(sub.weighted(weights).mean(dim=("lat", "lon"), skipna=True))


def extract(ds, needed, variables) -> dict:
    """Area mean for every (region, variable) wanted from one open dataset."""
    out = {}
    for v, rs in needed.items():
        da = ds[variables[v]["field"]]
        if "time" in da.dims:
            da = da.isel(time=0)
        for r in rs:
            out[(r["id"], v)] = area_mean(da, r["bbox"]) * variables[v]["scale"] + variables[v]["offset"]
    return out


# ---- access methods -------------------------------------------------------------------------

_local = threading.local()


def thread_session():
    if not hasattr(_local, "session"):
        _local.session = earthaccess.get_requests_https_session()
    return _local.session


def opendap_url(granule) -> str:
    for u in granule["umm"].get("RelatedUrls", []):
        if "OPENDAP" in str(u.get("Subtype", "")).upper():
            return u["URL"].split("?")[0]
    raise LookupError("no OPeNDAP link in this granule's metadata")


_state = {"ok": 0, "fail": 0}
_state_lock = threading.Lock()
OPENDAP_GIVE_UP_AFTER = 3  # failures with zero successes before a product falls back to streaming


def reset_method_state() -> None:
    with _state_lock:
        _state.update(ok=0, fail=0)


def _opendap_disabled() -> bool:
    with _state_lock:
        return _state["ok"] == 0 and _state["fail"] >= OPENDAP_GIVE_UP_AFTER


def _read_opendap(granule, short_name, needed, variables) -> dict:
    kw = {"group": GROUPS[short_name]} if short_name in GROUPS else {}
    with xr.open_dataset(opendap_url(granule), engine="pydap", session=thread_session(),
                         decode_times=False, **kw) as ds:
        return extract(ds, needed, variables)


def data_url(granule) -> str:
    """The plain HTTPS download link (not the S3 or documentation links)."""
    for u in granule["umm"].get("RelatedUrls", []):
        if u.get("Type") == "GET DATA" and str(u.get("URL", "")).startswith("http"):
            return u["URL"]
    raise LookupError("no HTTPS download link in this granule's metadata")


def _read_stream(granule, short_name, needed, variables) -> dict:
    """Download the whole file once into memory, then read every region from memory.
    (Reading straight from the remote file fetched large blocks again for each chunk.)"""
    resp = thread_session().get(data_url(granule), timeout=600)
    resp.raise_for_status()
    with xr.open_dataset(io.BytesIO(resp.content), engine="h5netcdf",
                         group=GROUPS.get(short_name), decode_times=False) as ds:
        return extract(ds, needed, variables)


def read_granule(granule, short_name, needed, variables, method) -> dict:
    """method: "opendap", "stream", or "auto" (OPeNDAP first, falling back to streaming)."""
    if method in ("opendap", "auto") and not _opendap_disabled():
        try:
            values = _read_opendap(granule, short_name, needed, variables)
            with _state_lock:
                _state["ok"] += 1
            return values
        except Exception as exc:
            if method == "opendap":
                raise
            with _state_lock:
                _state["fail"] += 1
                give_up = _state["ok"] == 0 and _state["fail"] == OPENDAP_GIVE_UP_AFTER
            if give_up:
                print(f"[{short_name}] OPeNDAP is not working for this product ({describe(exc)}); "
                      "downloading whole files instead (slower)", flush=True)
    return _read_stream(granule, short_name, needed, variables)


def read_with_retry(granule, short_name, needed, variables, method) -> dict:
    for attempt in range(1, RETRIES + 1):
        try:
            return read_granule(granule, short_name, needed, variables, method)
        except Exception:
            if attempt == RETRIES:
                raise
            time.sleep(2 * attempt)


# ---- saving ---------------------------------------------------------------------------------

def save(rows) -> None:
    DATA.mkdir(exist_ok=True)
    for (rid, v), lst in rows.items():
        if not lst:
            continue
        new = pd.DataFrame(lst)[["date", "value"]]
        p = cache_path(rid, v)
        if p.exists():
            new = pd.concat([pd.read_parquet(p), new])
        new = new.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
        new.to_parquet(p, index=False)
        lst.clear()


# ---- main loop ------------------------------------------------------------------------------

def process_product(short_name, var_ids, variables, regions, end, method, workers):
    needed = {v: [r for r in regions if v in r["variables"]] for v in var_ids}
    needed = {v: rs for v, rs in needed.items() if rs}
    if not needed:
        return

    start = min(pd.Timestamp(f"{variables[v]['start_year']}-01-01") for v in needed)
    print(f"[{short_name}] searching {start.date()} -> {end}", flush=True)
    results = earthaccess.search_data(
        short_name=short_name, version=VERSIONS[short_name],
        temporal=(start.strftime("%Y-%m-%d"), end + "-28"),
    )
    if not results:
        print("  nothing found: check short_name/version and your date range", file=sys.stderr)
        return

    # Skip months already cached for every variable of this product.
    have = set.intersection(*[cached_months([r["id"] for r in rs], v) for v, rs in needed.items()])
    todo = [g for g in results if granule_month(g) not in have]
    print(f"[{short_name}] {len(results)} granules, {len(results) - len(todo)} already cached, "
          f"{len(todo)} to fetch ({workers} workers, {method})", flush=True)
    if not todo:
        return

    reset_method_state()
    rows = {(r["id"], v): [] for v, rs in needed.items() for r in rs}
    done = ok = 0
    failed = []
    t0 = time.time()
    pool = ThreadPoolExecutor(max_workers=workers)
    futures = {pool.submit(read_with_retry, g, short_name, needed, variables, method): g for g in todo}
    try:
        for fut in as_completed(futures):
            g = futures[fut]
            done += 1
            try:
                values = fut.result()
                date = granule_month(g)
                for key, val in values.items():
                    rows[key].append({"date": date, "value": val})
                ok += 1
            except Exception as exc:
                failed.append((g["meta"]["concept-id"], describe(exc)))

            if done >= FAIL_FAST_AFTER and ok == 0:
                sys.exit(f"[{short_name}] the first {done} granules all failed ({failed[0][1]}). Stopping.\n"
                         "If status=403: authorize the NASA GESDISC DATA ARCHIVE application in your "
                         "Earthdata Login profile. Try --method stream to see the underlying error.")
            if done % 24 == 0 or done == len(todo):
                rate = done / (time.time() - t0)
                print(f"  {done}/{len(todo)}  ok={ok} failed={len(failed)}  "
                      f"eta {(len(todo) - done) / rate / 60:.0f} min", flush=True)
            if done % CHECKPOINT_EVERY == 0:
                save(rows)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        save(rows)
    if failed:
        print(f"[{short_name}] {len(failed)} granules failed, e.g. {failed[0]}. "
              "Re-run to retry only the missing months.", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vars", nargs="*", help="variable ids (default: all NetCDF ones)")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m"), help="YYYY-MM")
    ap.add_argument("--workers", type=int, default=10, help="parallel granules (default 10)")
    ap.add_argument("--method", choices=["auto", "opendap", "stream"], default="auto",
                    help="auto: OPeNDAP first, fall back to streaming per product (default)")
    args = ap.parse_args()

    variables, regions = load_catalog()
    earthaccess.login(persist=True)  # env vars, ~/.netrc, or an interactive prompt

    wanted = args.vars or list(variables)
    by_product: dict[str, list[str]] = {}
    for v in wanted:
        sn = variables[v]["short_name"]
        if sn in VERSIONS:
            by_product.setdefault(sn, []).append(v)
        else:
            print(f"skipping {v} ({sn}): HDF4 product, not handled by this script")
    for short_name, var_ids in by_product.items():
        process_product(short_name, var_ids, variables, regions, args.end, args.method, args.workers)
    print("done. Files are in", DATA)


if __name__ == "__main__":
    main()