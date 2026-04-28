"""conftest.py — Test configuration with APP_ENV=test isolation."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Inject common package path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common" / "src"))

# Set APP_ENV=test for isolated test DB (accounts_test.db)
os.environ["APP_ENV"] = "test"