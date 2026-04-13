"""conftest.py — Inject common package path before any test collection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common" / "src"))