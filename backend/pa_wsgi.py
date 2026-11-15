"""WSGI entry for PythonAnywhere: the Flask version of the API (see flask_app.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask_app import app as application  # noqa: E402,F401
