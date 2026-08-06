"""Application settings loaded from settings.json (user-editable via Preferences)."""

from __future__ import annotations

import json
import os
from copy import deepcopy

DEFAULT_SETTINGS = {
    "log_dir": "_logs",
    "temp_dir": "_temp",
    "nnunet_server_url": "https://nnunet-server-01.apps.myphysics.net/api/v3",
    "keycloak_url": "https://login.apps.myphysics.net",
    "keycloak_realm": "myphysics",
    "keycloak_registration_url": (
        "https://login.apps.myphysics.net/realms/myphysics/protocol/openid-connect/registrations"
        "?client_id=account-console&response_type=code&scope=openid"
        "&redirect_uri=https%3A%2F%2Flogin.apps.myphysics.net%2Frealms%2Fmyphysics%2Faccount%2F"
    ),
}

# Mutable singleton returned by get_config(); Preferences updates it in place.
_config = None


def settings_path():
    """settings.json lives in the process working directory (app launch dir)."""
    return os.path.abspath(os.path.join(os.getcwd(), "settings.json"))


def _ensure_dirs(cfg: dict):
    for key in ("log_dir", "temp_dir"):
        path = cfg.get(key)
        if path and not os.path.exists(path):
            os.makedirs(path, exist_ok=True)


def _normalize(data: dict) -> dict:
    cfg = deepcopy(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        for key in DEFAULT_SETTINGS:
            if key in data and data[key] is not None:
                cfg[key] = data[key]
    # Keep registration URL as string
    cfg["keycloak_registration_url"] = str(cfg.get("keycloak_registration_url") or "").strip()
    cfg["nnunet_server_url"] = str(cfg.get("nnunet_server_url") or "").strip()
    cfg["keycloak_url"] = str(cfg.get("keycloak_url") or "").strip()
    cfg["keycloak_realm"] = str(cfg.get("keycloak_realm") or "").strip()
    cfg["log_dir"] = str(cfg.get("log_dir") or DEFAULT_SETTINGS["log_dir"]).strip()
    cfg["temp_dir"] = str(cfg.get("temp_dir") or DEFAULT_SETTINGS["temp_dir"]).strip()
    return cfg


def load_settings(path=None) -> dict:
    path = path or settings_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = _normalize(data)
    else:
        cfg = _normalize({})
        save_settings(cfg, path=path)
    _ensure_dirs(cfg)
    return cfg


def save_settings(cfg: dict, path=None) -> dict:
    """Write settings.json and update the in-memory singleton."""
    global _config
    path = path or settings_path()
    normalized = _normalize(cfg)
    _ensure_dirs(normalized)

    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)
        f.write("\n")

    if _config is None:
        _config = normalized
    else:
        _config.clear()
        _config.update(normalized)
    return _config


def get_config() -> dict:
    """Return the shared settings dict (always the same object)."""
    global _config
    if _config is None:
        _config = load_settings()
        print("get_config().return=", _config)
    return _config


def reload_config() -> dict:
    """Force reload from disk into the singleton."""
    global _config
    loaded = load_settings()
    if _config is None:
        _config = loaded
    else:
        _config.clear()
        _config.update(loaded)
    return _config
