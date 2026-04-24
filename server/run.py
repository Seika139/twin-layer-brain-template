from __future__ import annotations

import uvicorn

from compiler.env import load_dotenv

load_dotenv()

from compiler.config import SERVER_HOST, SERVER_PORT  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("server.app:app", host=SERVER_HOST, port=SERVER_PORT)
