from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DOWNLOAD_DIR = BASE_DIR / "downloads"

DATABASE_PATH = Path(
    os.getenv("TESTLAB_DB_PATH", str(DATA_DIR / "testlab.db"))
).resolve()
TOKEN_SECRET = os.getenv(
    "TESTLAB_SECRET", "fastapi-test-lab-local-demo-secret-change-if-exposed"
)
TOKEN_TTL_SECONDS = int(os.getenv("TESTLAB_TOKEN_TTL", "3600"))
MAX_UPLOAD_BYTES = 512 * 1024

APP_NAME = "FastAPI Test Lab"
APP_VERSION = "1.0.0"

