"""Start the local development API with workspace-local dependencies."""

import sys
from pathlib import Path


LOCAL_DEPS = Path(__file__).resolve().parent / ".runtime-deps"
if LOCAL_DEPS.exists():
    sys.path.append(str(LOCAL_DEPS))

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        ws_max_size=32_768,
        ws_per_message_deflate=False,
    )
