"""Write backend/data/regions.geojson: the region boxes as polygons, for uploading
to the AppEEARS Area Sampler (MODIS NDVI / LST).

    python scripts/make_regions_geojson.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
regions = json.loads((ROOT / "app" / "catalog" / "regions.json").read_text())["regions"]

features = []
for r in regions:
    w, s, e, n = r["bbox"]
    features.append({
        "type": "Feature",
        "properties": {"id": r["id"], "name": r["name"]},
        "geometry": {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]},
    })

out = ROOT / "data" / "regions.geojson"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=1))
print(f"Wrote {len(features)} polygons to {out}")