"""Run the quant API locally:  python -m ai_trader_optimizer.api  (127.0.0.1:8765 by default).

Binding to a non-loopback address requires ATO_API_ALLOW_REMOTE=1 (never expose it publicly:
there is no authentication; it is a single-user local research tool).
"""

import os
import sys

import uvicorn

from .app import create_app

LOOPBACK = {"127.0.0.1", "localhost", "::1"}

if __name__ == "__main__":
    host = os.environ.get("ATO_API_HOST", "127.0.0.1")
    port = int(os.environ.get("ATO_API_PORT", "8765"))
    if host not in LOOPBACK and os.environ.get("ATO_API_ALLOW_REMOTE") != "1":
        sys.exit(f"Refus d'écouter sur {host!r} : API locale uniquement (ATO_API_ALLOW_REMOTE=1 pour forcer).")
    uvicorn.run(create_app(), host=host, port=port, log_level=os.environ.get("ATO_API_LOG_LEVEL", "info"))
