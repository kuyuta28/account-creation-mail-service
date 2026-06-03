"""
main.py — Start Mail Service server.

Port mặc định: 8701
Override: MAIL_HOST / MAIL_PORT env vars

Usage:
  python main.py
  MAIL_PORT=9001 python main.py
"""
import os
import sys
from pathlib import Path

# Inject common package
sys.path.insert(0, str(Path(__file__).parent.parent / "common" / "src"))

import uvicorn

if sys.platform == "win32":
    import uvicorn.loops.asyncio as _uvloop
    _uvloop.asyncio_setup = lambda use_subprocess=False: None

if __name__ == "__main__":
    uvicorn.run(
        "src.mail_service.server:app",
        host=os.getenv("MAIL_HOST", "127.0.0.1"),
        port=int(os.getenv("MAIL_PORT", "8701")),
        reload=False,
    )
