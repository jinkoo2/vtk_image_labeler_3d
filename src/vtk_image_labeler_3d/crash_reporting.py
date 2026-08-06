"""Crash / exception reporting to BugSink (Sentry-compatible)."""

from __future__ import annotations

import logging
import sys
import threading
import traceback

# Public client DSN (safe to embed in desktop apps).
BUGSINK_DSN = (
    "https://688975074f4442d5aa60cad54851ba6c@bugsink.apps.myphysics.net/4"
)

_initialized = False


def init_crash_reporting(release: str | None = None) -> bool:
    """
    Initialize BugSink via sentry-sdk.

    Returns True if reporting is active.
    """
    global _initialized
    if _initialized:
        return True

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logging.getLogger(__name__).warning(
            "sentry-sdk is not installed; BugSink crash reporting is disabled."
        )
        return False

    if not (BUGSINK_DSN or "").strip():
        return False

    try:
        from version_info import get_version

        ver = release or get_version()
    except Exception:
        ver = release or "unknown"

    try:
        sentry_sdk.init(
            dsn=BUGSINK_DSN.strip(),
            release=f"vtk-image-labeler-3d@{ver}",
            environment="desktop",
            send_default_pii=False,
            traces_sample_rate=0.0,
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("BugSink init failed: %s", exc)
        return False

    _install_exception_hooks()
    _initialized = True
    logging.getLogger(__name__).info("BugSink crash reporting enabled")
    return True


def _install_exception_hooks() -> None:
    import sentry_sdk

    previous = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_tb):
        try:
            if exc_value is not None:
                sentry_sdk.capture_exception(exc_value)
            else:
                sentry_sdk.capture_exception()
        except Exception:
            pass
        if previous is not None:
            previous(exc_type, exc_value, exc_tb)
        else:
            sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    if hasattr(threading, "excepthook"):
        previous_thread = threading.excepthook

        def _thread_excepthook(args):
            try:
                if getattr(args, "exc_value", None) is not None:
                    sentry_sdk.capture_exception(args.exc_value)
            except Exception:
                pass
            try:
                previous_thread(args)
            except Exception:
                pass

        threading.excepthook = _thread_excepthook


def capture_exception(exc: BaseException | None = None) -> None:
    """Send an exception to BugSink if reporting is initialized."""
    if not _initialized:
        return
    try:
        import sentry_sdk

        if exc is None:
            sentry_sdk.capture_exception()
        else:
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def capture_message(message: str, level: str = "error") -> None:
    if not _initialized:
        return
    try:
        import sentry_sdk

        sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass
