"""HTTP client for the Observatory API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

DEFAULT_SERVER_URL = "https://api.observatory.softmax-research.net"
TOKEN_FILE = Path.home() / ".metta" / "config.yaml"


def load_observatory_token(server_url: str = DEFAULT_SERVER_URL) -> str | None:
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE) as f:
        data = yaml.safe_load(f) or {}
    tokens = data.get("observatory_tokens", {})
    token = tokens.get(server_url)
    return token if isinstance(token, str) else None


class ObservatoryClient:
    def __init__(self, server_url: str = DEFAULT_SERVER_URL, token: str | None = None):
        self.server_url = server_url.rstrip("/")
        self.token = token or load_observatory_token(server_url)
        self._client: httpx.AsyncClient | None = None

    @property
    def authenticated(self) -> bool:
        return self.token is not None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.AsyncClient(
                base_url=self.server_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        client = await self._get_client()
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, json: Any = None) -> Any:
        client = await self._get_client()
        resp = await client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
