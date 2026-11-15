"""Build frontend/public/regions.geojson: real-world outlines for the 7 regions.

    pip install shapely requests
    python scripts/make_region_shapes.py

Source: Natural Earth (public domain), https://github.com/nvkelso/natural-earth-vector
  - ne_10m_geography_regions_polys : SAHEL, GANGES PLAIN, Central Valley, KARAKORAM RA., HINDU KUSH, AMAZON BASIN
  - ne_10m_geography_marine_polys  : Barents Sea
  - ne_10m_lakes                   : North and South Aral Sea

Each region's outline is a Natural Earth feature, optionally clipped to the analysis box
(Amazon arc, Upper Indus, Barents). Prints how much of each outline the data box covers.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "public" / "regions.geojson"
REGIONS = json.loads((ROOT / "backend/app/catalog/regions.json").read_text())["regions"]
BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"


def load(name):
    r = requests.get(BASE + name + ".geojson", timeout=180)
    r.raise_for_status()
    return r.json()["features"]


def pick(features, key, names):
    return unary_union([shape(f["geometry"]) for f in features if f["properties"].get(key) in names])


def main():
    land = load("ne_10m_geography_regions_polys")
    sea = load("ne_10m_geography_marine_polys")
    lakes = load("ne_10m_lakes")
    boxes = {r["id"]: box(*r["bbox"]) for r in REGIONS}

    raw = {
        "sahel": (pick(land, "NAME", {"SAHEL"}), "Natural Earth: Sahel"),
        "indo_gangetic": (pick(land, "NAME", {"GANGES PLAIN"}), "Natural Earth: Ganges Plain"),
        "central_valley": (pick(land, "NAME", {"Central Valley"}), "Natural Earth: Central Valley"),
        "amazon_arc": (pick(land, "NAME", {"AMAZON BASIN"}).intersection(boxes["amazon_arc"]),
                       "Natural Earth: Amazon Basin, clipped to the southern and eastern arc"),
        "upper_indus": (pick(land, "NAME", {"KARAKORAM RA.", "HINDU KUSH"}).intersection(boxes["upper_indus"]),
                        "Natural Earth: Karakoram and Hindu Kush ranges, clipped to the Upper Indus box"),
        "arctic_barents": (pick(sea, "name", {"Barents Sea"}).intersection(boxes["arctic_barents"]),
                           "Natural Earth: Barents Sea, clipped to the analysis box"),
        "aral_sea": (pick(lakes, "name", {"North Aral Sea", "South Aral Sea"}).buffer(0.75)
                     .intersection(boxes["aral_sea"]),
                     "Natural Earth: Aral Sea lakes, widened by 0.75 degrees to show the basin around them"),
    }

    feats = []
    print(f"{'region':16s} {'shape in box':>13s} {'box in shape':>13s}")
    for r in REGIONS:
        geom, source = raw[r["id"]]
        geom = geom.simplify(0.02, preserve_topology=True)
        inter = geom.intersection(boxes[r["id"]]).area
        shape_in_box = inter / geom.area
        box_in_shape = inter / boxes[r["id"]].area
        print(f"{r['id']:16s} {shape_in_box:13.0%} {box_in_shape:13.0%}")
        c = geom.representative_point()
        feats.append({"type": "Feature", "id": r["id"], "geometry": mapping(geom),
                      "properties": {"id": r["id"], "source": source,
                                     "shape_in_box": round(shape_in_box, 3),
                                     "box_in_shape": round(box_in_shape, 3),
                                     "label": [round(c.x, 3), round(c.y, 3)]}})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                              separators=(",", ":")))
    print("wrote", OUT, f"{OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
