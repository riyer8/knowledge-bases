from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from core.config import config

_TOKEN_DIR = config.auth_dir


def token_path(service: str) -> Path:
    return _TOKEN_DIR / f"{service}_token.json"


def load_token(service: str) -> Optional[dict]:
    path = token_path(service)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_token(service: str, token: dict) -> None:
    _TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    path = token_path(service)
    path.write_text(json.dumps(token, indent=2))
    path.chmod(0o600)


def is_expired(token: dict, buffer_seconds: int = 120) -> bool:
    expires_at = token.get("expires_at", 0)
    return time.time() >= (expires_at - buffer_seconds)


def refresh_token(service: str, client_id: str, client_secret: str) -> dict:
    token = load_token(service)
    if not token or not token.get("refresh_token"):
        raise RuntimeError(f"{service}: no refresh token — re-authenticate via /integrations/{service}/auth")

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=urllib.parse.urlencode(params).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        new_token = json.loads(resp.read())

    new_token["refresh_token"] = token["refresh_token"]
    new_token["expires_at"] = time.time() + new_token.get("expires_in", 3600)
    save_token(service, new_token)
    return new_token


def get_access_token(service: str, client_id: str, client_secret: str) -> str:
    token = load_token(service)
    if not token:
        raise RuntimeError(f"{service}: not connected — open Settings → Connections to authenticate")
    if is_expired(token):
        token = refresh_token(service, client_id, client_secret)
    return token["access_token"]


def build_auth_url(
    client_id: str,
    scopes: list[str],
    redirect_uri: str,
    state: str = "",
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    params = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=urllib.parse.urlencode(params).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        token = json.loads(resp.read())
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    return token
