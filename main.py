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

# Inject any-auto-register vào sys.path để aar_adapter.py có thể import core.base_mailbox
_AAR_PATH = Path(__file__).parent / "any-auto-register"
if _AAR_PATH.exists() and str(_AAR_PATH) not in sys.path:
    sys.path.insert(0, str(_AAR_PATH))

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
