"""Create FAKE data in backend/data_synthetic for frontend development.

    python scripts/make_synthetic_cache.py
    DATA_DIR=data_synthetic uvicorn app.main:app --reload
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.synthetic import make_cache

make_cache(ROOT / "data_synthetic")
print("Wrote FAKE data to", ROOT / "data_synthetic")