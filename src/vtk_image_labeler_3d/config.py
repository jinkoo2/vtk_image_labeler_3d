"""Application settings loaded from settings.json (user-editable via Preferences)."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from urllib.parse import urlparse

_DEFAULT_SERVER_URLS = [
    "https://nnunet-server-01.apps.myphysics.net/api/v3",
    "https://nnunet-server-02.apps.myphysics.net/api/v3",
]

# Canonical settings key for the server list (legacy key: nnunet_server_url).
SERVER_URL_LIST_KEY = "nnunet_server_url_list"
_LEGACY_SERVER_URL_KEY = "nnunet_server_url"

DEFAULT_SETTINGS = {
    "log_dir": "_logs",
    "temp_dir": "_temp",
    # List of nnU-Net API roots used for Connect dropdown + prediction load balancing.
    SERVER_URL_LIST_KEY: list(_DEFAULT_SERVER_URLS),
    # Currently selected server (must be one of the list when possible).
    "nnunet_selected_server_url": _DEFAULT_SERVER_URLS[0],
    "keycloak_url": "https://login.apps.myphysics.net",
    "keycloak_realm": "myphysics",
    # Account Console starts OIDC with PKCE. Do not use /openid-connect/registrations
    # against account-console — that client requires code_challenge_method.
    "keycloak_registration_url": "https://login.apps.myphysics.net/realms/myphysics/account/",
    # CapRover feedback API origin (no path). Empty = fall back to opening GitHub Issues.
    "feedback_api_url": "",
    # Optional shared secret; must match server FEEDBACK_API_KEY when set.
    "feedback_api_key": "",
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


def _normalize_server_urls(value) -> list:
    """Accept a string or list; return a cleaned non-empty URL list."""
    if isinstance(value, str):
        urls = [value]
    elif isinstance(value, (list, tuple)):
        urls = list(value)
    else:
        urls = []

    cleaned = []
    seen = set()
    for item in urls:
        url = str(item or "").strip().rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)
        cleaned.append(url)
    return cleaned or list(_DEFAULT_SERVER_URLS)


def _server_url_list_from_raw(data: dict):
    """Prefer nnunet_server_url_list; fall back to legacy nnunet_server_url."""
    if not isinstance(data, dict):
        return None
    if SERVER_URL_LIST_KEY in data and data[SERVER_URL_LIST_KEY] is not None:
        return data[SERVER_URL_LIST_KEY]
    if _LEGACY_SERVER_URL_KEY in data and data[_LEGACY_SERVER_URL_KEY] is not None:
        return data[_LEGACY_SERVER_URL_KEY]
    return None


def default_registration_url(keycloak_url: str = "", realm: str = "") -> str:
    """Keycloak Account Console. The SPA starts login with PKCE, then Register."""
    base = (keycloak_url or "").rstrip("/") or DEFAULT_SETTINGS["keycloak_url"]
    realm = (realm or "").strip() or DEFAULT_SETTINGS["keycloak_realm"]
    return f"{base}/realms/{realm}/account/"


def _is_pkce_less_account_console_registration(url: str) -> bool:
    """True for the static registrations URL that Keycloak 26 rejects."""
    lowered = (url or "").lower()
    return (
        "/protocol/openid-connect/registrations" in lowered
        and "client_id=account-console" in lowered
        and "code_challenge" not in lowered
    )


_ACCOUNT_CONSOLE_PATH = re.compile(r"^/realms/[^/]+/account/?$", re.I)


def _is_account_console_url(url: str) -> bool:
    return bool(_ACCOUNT_CONSOLE_PATH.match(urlparse(url).path or ""))


def _coerce_registration_url(url: str, keycloak_url: str, realm: str) -> str:
    raw = str(url or "").strip()
    if (
        not raw
        or _is_pkce_less_account_console_registration(raw)
        or _is_account_console_url(raw)
    ):
        return default_registration_url(keycloak_url, realm)
    return raw


def get_nnunet_server_urls(cfg: dict | None = None) -> list:
    """Return configured nnU-Net server URL list."""
    cfg = cfg if cfg is not None else get_config()
    return list(cfg.get(SERVER_URL_LIST_KEY) or _DEFAULT_SERVER_URLS)


def get_nnunet_server_url(cfg: dict | None = None) -> str:
    """Return the currently selected nnU-Net server URL."""
    cfg = cfg if cfg is not None else get_config()
    urls = get_nnunet_server_urls(cfg)
    selected = str(cfg.get("nnunet_selected_server_url") or "").strip().rstrip("/")
    if selected and selected in urls:
        return selected
    return urls[0] if urls else _DEFAULT_SERVER_URLS[0]


def set_nnunet_selected_server_url(url: str, persist: bool = True) -> str:
    """Update the selected server URL in memory (and optionally settings.json)."""
    cfg = get_config()
    urls = get_nnunet_server_urls(cfg)
    selected = str(url or "").strip().rstrip("/")
    if selected not in urls:
        # Allow connecting to a URL typed/selected even if not yet in list.
        if selected:
            urls = list(urls) + [selected]
            cfg[SERVER_URL_LIST_KEY] = urls
        else:
            selected = urls[0] if urls else _DEFAULT_SERVER_URLS[0]
    cfg["nnunet_selected_server_url"] = selected
    if persist:
        save_settings(cfg)
    return selected


def _normalize(data: dict) -> dict:
    cfg = deepcopy(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        for key in DEFAULT_SETTINGS:
            if key in data and data[key] is not None:
                cfg[key] = data[key]
        raw_urls = _server_url_list_from_raw(data)
        if raw_urls is not None:
            cfg[SERVER_URL_LIST_KEY] = raw_urls
        if "nnunet_selected_server_url" in data and data["nnunet_selected_server_url"]:
            cfg["nnunet_selected_server_url"] = data["nnunet_selected_server_url"]

    cfg[SERVER_URL_LIST_KEY] = _normalize_server_urls(cfg.get(SERVER_URL_LIST_KEY))
    selected = str(cfg.get("nnunet_selected_server_url") or "").strip().rstrip("/")
    if selected not in cfg[SERVER_URL_LIST_KEY]:
        selected = cfg[SERVER_URL_LIST_KEY][0]
    cfg["nnunet_selected_server_url"] = selected
    cfg["keycloak_url"] = str(cfg.get("keycloak_url") or "").strip()
    cfg["keycloak_realm"] = str(cfg.get("keycloak_realm") or "").strip()
    cfg["keycloak_registration_url"] = _coerce_registration_url(
        cfg.get("keycloak_registration_url"),
        cfg["keycloak_url"],
        cfg["keycloak_realm"],
    )
    cfg["log_dir"] = str(cfg.get("log_dir") or DEFAULT_SETTINGS["log_dir"]).strip()
    cfg["temp_dir"] = str(cfg.get("temp_dir") or DEFAULT_SETTINGS["temp_dir"]).strip()
    cfg["feedback_api_url"] = str(cfg.get("feedback_api_url") or "").strip().rstrip("/")
    cfg["feedback_api_key"] = str(cfg.get("feedback_api_key") or "").strip()
    # Drop legacy key from the in-memory/on-disk shape.
    cfg.pop(_LEGACY_SERVER_URL_KEY, None)
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
