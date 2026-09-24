"""Headless smoke tests for GitHub Actions."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1] / "src" / "vtk_image_labeler_3d"
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))


def _fake_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"


def test_package_imports():
    import config
    import itk_tools
    import nnunet_service

    assert callable(config.get_config)
    assert callable(itk_tools.combine_sitk_labels)
    assert callable(nnunet_service.has_nnunet_train_role)


def test_config_defaults(tmp_path, monkeypatch):
    import config

    monkeypatch.chdir(tmp_path)
    config._config = None
    conf = config.get_config()
    assert conf["log_dir"]
    assert conf["nnunet_server_url_list"]
    assert (tmp_path / "settings.json").exists()

    assert conf["keycloak_registration_url"].endswith("/realms/myphysics/account/")
    conf["keycloak_realm"] = "ci-realm"
    config.save_settings(conf)
    config._config = None
    conf2 = config.get_config()
    assert conf2["keycloak_realm"] == "ci-realm"
    assert conf2["keycloak_registration_url"].endswith("/realms/ci-realm/account/")


def test_legacy_account_console_registration_url_is_rewritten(tmp_path, monkeypatch):
    import config

    monkeypatch.chdir(tmp_path)
    config._config = None
    broken = (
        "https://login.apps.myphysics.net/realms/myphysics/protocol/openid-connect/registrations"
        "?client_id=account-console&response_type=code&scope=openid"
        "&redirect_uri=https%3A%2F%2Flogin.apps.myphysics.net%2Frealms%2Fmyphysics%2Faccount%2F"
    )
    (tmp_path / "settings.json").write_text(
        '{"keycloak_registration_url": "%s"}\n' % broken,
        encoding="utf-8",
    )
    conf = config.get_config()
    assert conf["keycloak_registration_url"] == (
        "https://login.apps.myphysics.net/realms/myphysics/account/"
    )
    assert "openid-connect/registrations" not in conf["keycloak_registration_url"]


def test_nnunet_train_role_from_jwt():
    import nnunet_service

    nnunet_service.clear_auth_session()
    assert not nnunet_service.has_nnunet_train_role()

    token = _fake_jwt(
        {
            "preferred_username": "user@example.com",
            "realm_access": {"roles": ["nnunet-train", "offline_access"]},
        }
    )
    nnunet_service.set_auth_session(token, user_email="user@example.com", is_admin=False)
    assert nnunet_service.has_nnunet_train_role()
    assert nnunet_service.has_role("nnunet-train")
    assert not nnunet_service.has_role("nnunet-admin")

    nnunet_service.clear_auth_session()
    assert not nnunet_service.has_nnunet_train_role()


def test_pyqt_offscreen_app():
    from PyQt5.QtWidgets import QApplication, QLabel

    app = QApplication.instance() or QApplication([])
    label = QLabel("ci")
    label.show()
    app.processEvents()
    assert label.text() == "ci"
