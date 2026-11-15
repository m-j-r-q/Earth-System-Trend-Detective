"""Time ONE MERRA-2 granule with two access methods, to find out why the cache build is slow.

    pip install pydap
    python scripts/benchmark_access.py

Method A: stream the whole HDF5 file over HTTPS (what build_cache.py does now).
Method B: OPeNDAP, where the server cuts out only the requested box.
Paste the whole output back. It contains no credentials.
"""
from __future__ import annotations

import sys
import time

import earthaccess
import numpy as np
import xarray as xr

BBOX = (-15, 10, 20, 17)  # Sahel: west, south, east, north
FIELD = "T2M"


def describe(exc: Exception) -> str:
    return f"{type(exc).__name__} status={getattr(exc, 'status', None)}: {str(exc)[:120].splitlines()[0]}"


def area_mean(da):
    w, s, e, n = BBOX
    sub = da.sel(lat=slice(s, n), lon=slice(w, e))
    return float(sub.weighted(np.cos(np.deg2rad(sub["lat"]))).mean(dim=("lat", "lon")))


earthaccess.login(persist=True)
g = earthaccess.search_data(short_name="M2TMNXSLV", version="5.12.4",
                            temporal=("2000-01-01", "2000-01-31"))[0]
try:
    print(f"granule size: {g.size()} MB")
except Exception as exc:
    print("size unknown:", describe(exc))

print("\nRelated URLs (type / subtype):")
opendap = None
for u in g["umm"].get("RelatedUrls", []):
    print(" ", u.get("Type"), "/", u.get("Subtype"), "/", u["URL"][:110])
    if "OPENDAP" in str(u.get("Subtype", "")).upper() and opendap is None:
        opendap = u["URL"]

print("\n--- Method A: stream HDF5 ---")
try:
    t0 = time.time()
    f = earthaccess.open([g])[0]
    t1 = time.time()
    with xr.open_dataset(f, engine="h5netcdf", decode_times=False) as ds:
        t2 = time.time()
        da = ds[FIELD].isel(time=0)
        print("chunks:", ds[FIELD].encoding.get("chunksizes"))
        val = area_mean(da)
        t3 = time.time()
    print(f"open handle {t1 - t0:.1f}s | open dataset {t2 - t1:.1f}s | read+mean {t3 - t2:.1f}s | "
          f"total {t3 - t0:.1f}s | value {val:.2f} K")
except Exception as exc:
    print("failed:", describe(exc))

print("\n--- Method B: OPeNDAP ---")
if not opendap:
    print("no OPeNDAP link in this granule's metadata")
    sys.exit()
url = opendap.split("?")[0]
print("url:", url)
try:
    t0 = time.time()
    session = earthaccess.get_requests_https_session()
    with xr.open_dataset(url, engine="pydap", session=session, decode_times=False) as ds:
        t1 = time.time()
        da = ds[FIELD]
        if "time" in da.dims:
            da = da.isel(time=0)
        val = area_mean(da)
        t2 = time.time()
    print(f"open {t1 - t0:.1f}s | read+mean {t2 - t1:.1f}s | total {t2 - t0:.1f}s | value {val:.2f} K")
except Exception as exc:
    print("failed:", describe(exc))