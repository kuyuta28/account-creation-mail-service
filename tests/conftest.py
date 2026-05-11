"""conftest.py — Test configuration with APP_ENV=test isolation."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = REPO_ROOT.parent

for package_path in (REPO_ROOT / "src", WORKSPACE_ROOT / "common" / "src"):
    sys.path.insert(0, str(package_path))

# Set APP_ENV=test for isolated test DB (accounts_test.db)
os.environ["APP_ENV"] = "test"