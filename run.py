#!/usr/bin/env python3
"""Quick start: python run.py"""

from dragonboat.database import init_db

init_db()

import uvicorn
from dragonboat.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "dragonboat.web.app:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
