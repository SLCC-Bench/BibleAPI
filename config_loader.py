"""Load BibleAPI desktop/local configuration from env and optional JSON files."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _candidate_config_paths() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("BIBLEAPI_CONFIG")
    if explicit:
        paths.append(Path(explicit))

    # Next to frozen binary (PyInstaller) or this source file
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve().parent / "bibleapi.env.json")
    else:
        paths.append(Path(__file__).resolve().parent / "bibleapi.env.json")

    cwd = Path.cwd() / "bibleapi.env.json"
    if cwd not in paths:
        paths.append(cwd)
    return paths


def _default_ssl_ca() -> str:
    if os.environ.get("MYSQL_SSL_CA"):
        return os.environ["MYSQL_SSL_CA"]
    try:
        import certifi
        return certifi.where()
    except Exception:
        pass
    # Common system CA bundles
    for candidate in (
        "/etc/ssl/cert.pem",  # macOS
        "/etc/ssl/certs/ca-certificates.crt",  # Linux
    ):
        if Path(candidate).exists():
            return candidate
    return ""


def load_config_into_environ() -> dict:
    """
    Merge bibleapi.env.json (if present) into os.environ without overwriting
    values already set in the environment. Returns the resolved config dict.
    """
    file_cfg: dict = {}
    for path in _candidate_config_paths():
        if path.is_file():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    file_cfg = data
                    print(f"[config] loaded {path}")
                    break
            except Exception as exc:
                print(f"[config] failed to read {path}: {exc}")

    key_map = {
        "MYSQL_HOST": "MYSQL_HOST",
        "MYSQL_PORT": "MYSQL_PORT",
        "MYSQL_USER": "MYSQL_USER",
        "MYSQL_PASSWORD": "MYSQL_PASSWORD",
        "MYSQL_DB": "MYSQL_DB",
        "MYSQL_DATABASE": "MYSQL_DB",
        "MYSQL_SSL_CA": "MYSQL_SSL_CA",
        "MYSQL_SSL": "MYSQL_SSL",
        "PORT": "PORT",
        "HMAC_SECRET": "HMAC_SECRET",
        "BIBLEAPI_LOCAL": "BIBLEAPI_LOCAL",
        "host": "MYSQL_HOST",
        "port": "MYSQL_PORT",
        "user": "MYSQL_USER",
        "password": "MYSQL_PASSWORD",
        "database": "MYSQL_DB",
        "db": "MYSQL_DB",
        "ssl_ca": "MYSQL_SSL_CA",
        "hmac_secret": "HMAC_SECRET",
        "api_port": "PORT",
    }

    for src_key, env_key in key_map.items():
        if src_key not in file_cfg:
            continue
        if os.environ.get(env_key):
            continue
        val = file_cfg[src_key]
        if val is None:
            continue
        os.environ[env_key] = str(val)

    # Desktop local mode defaults
    if not os.environ.get("BIBLEAPI_LOCAL"):
        # Frozen binary implies local desktop mode
        if getattr(sys, "frozen", False):
            os.environ["BIBLEAPI_LOCAL"] = "1"

    if not os.environ.get("PORT"):
        os.environ["PORT"] = "5000"

    if not os.environ.get("MYSQL_SSL_CA") and (
        os.environ.get("BIBLEAPI_LOCAL") == "1"
        or os.environ.get("MYSQL_SSL", "").lower() == "true"
        or "tidbcloud.com" in os.environ.get("MYSQL_HOST", "")
    ):
        ca = _default_ssl_ca()
        if ca:
            os.environ["MYSQL_SSL_CA"] = ca

    return {
        "MYSQL_HOST": os.environ.get("MYSQL_HOST", ""),
        "MYSQL_PORT": os.environ.get("MYSQL_PORT", "3306"),
        "MYSQL_USER": os.environ.get("MYSQL_USER", ""),
        "MYSQL_DB": os.environ.get("MYSQL_DB", ""),
        "PORT": os.environ.get("PORT", "5000"),
        "BIBLEAPI_LOCAL": os.environ.get("BIBLEAPI_LOCAL", "0"),
        "has_password": bool(os.environ.get("MYSQL_PASSWORD")),
        "MYSQL_SSL_CA": os.environ.get("MYSQL_SSL_CA", ""),
    }
