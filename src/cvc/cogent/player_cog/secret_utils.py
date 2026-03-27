from __future__ import annotations

import os
from pathlib import Path


def resolve_api_key(
    *,
    direct_value: str | None,
    file_path: str | Path | None,
    env_var: str,
    fallback_env_var: str | None = None,
    required: bool = True,
) -> str | None:
    if direct_value:
        stripped = direct_value.strip()
        if stripped:
            return stripped

    if file_path:
        try:
            return Path(file_path).read_text().strip()
        except (FileNotFoundError, PermissionError):
            pass

    value = os.getenv(env_var)
    if value:
        return value.strip()

    if fallback_env_var:
        value = os.getenv(fallback_env_var)
        if value:
            return value.strip()

    if required:
        sources = [env_var]
        if fallback_env_var:
            sources.append(fallback_env_var)
        raise RuntimeError(
            f"API key not found. Set one of: {', '.join(sources)}"
        )

    return None
