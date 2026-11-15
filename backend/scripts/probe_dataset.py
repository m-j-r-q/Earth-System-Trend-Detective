"""Show what OPeNDAP exposes for one granule of a product: file size and variable names.

    python scripts/probe_dataset.py GPM_3IMERGM 07 --find precip
    python scripts/probe_dataset.py GLDAS_NOAH025_M 2.1 --find evap

Paste the output back. It contains no credentials.
"""
import argparse
import warnings

import earthaccess
import xarray as xr

warnings.filterwarnings("ignore")

ap = argparse.ArgumentParser()
ap.add_argument("short_name")
ap.add_argument("version")
ap.add_argument("--find", default="", help="only list variables whose name contains this text")
ap.add_argument("--date", default="2010-06-01")
args = ap.parse_args()

earthaccess.login(persist=True)
g = earthaccess.search_data(short_name=args.short_name, version=args.version,
                            temporal=(args.date, args.date[:8] + "28"))[0]
print(f"granule size: {g.size():.1f} MB")
urls = [u["URL"].split("?")[0] for u in g["umm"].get("RelatedUrls", []) if "OPENDAP" in str(u.get("Subtype", "")).upper()]
print("opendap url:", urls[0] if urls else "none")
if urls:
    try:
        with xr.open_dataset(urls[0], engine="pydap", session=earthaccess.get_requests_https_session(),
                             decode_times=False) as ds:
            names = [n for n in list(ds.variables) if args.find.lower() in n.lower()]
            print(f"{len(ds.variables)} variables; matching '{args.find}':")
            for n in names[:40]:
                print("  ", n, ds[n].dims, ds[n].shape)
    except Exception as exc:
        print("could not open:", f"{type(exc).__name__}: {str(exc)[:160]}")