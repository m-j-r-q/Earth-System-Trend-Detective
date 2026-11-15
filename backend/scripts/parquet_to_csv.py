"""Convert the parquet cache to CSV (for hosts where pyarrow is not installed).

    python scripts/parquet_to_csv.py            # backend/data/*.parquet -> backend/data/*.csv
"""
import sys
from pathlib import Path

import pandas as pd

data = Path(__file__).resolve().parents[1] / (sys.argv[1] if len(sys.argv) > 1 else "data")
files = sorted(data.glob("*.parquet"))
for p in files:
    pd.read_parquet(p).to_csv(p.with_suffix(".csv"), index=False, date_format="%Y-%m-%d")
print(f"converted {len(files)} files in {data}")
