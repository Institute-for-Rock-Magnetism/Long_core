"""Crash-safe JSON persistence and structured rotating application logging."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .config import ApplicationConfig, ConfigValidationError


class ConfigCorruptionError(RuntimeError):
    """Raised when neither the primary configuration nor its backup is usable."""

    def __init__(self, path: Path, message: str, quarantine_path: Path | None = None):
        super().__init__(message)
        self.path = path
        self.quarantine_path = quarantine_path


def _sync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(
    path: str | Path,
    data: Mapping[str, Any],
    *,
    create_backup: bool = True,
) -> None:
    """Write JSON atomically, preserving the previous file as ``.bak``."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        if create_backup and target.exists():
            backup = target.with_suffix(target.suffix + ".bak")
            backup_descriptor, backup_temp_name = tempfile.mkstemp(
                prefix=f".{backup.name}.", suffix=".tmp", dir=target.parent
            )
            os.close(backup_descriptor)
            try:
                shutil.copy2(target, backup_temp_name)
                with open(backup_temp_name, "rb") as backup_handle:
                    os.fsync(backup_handle.fileno())
                os.replace(backup_temp_name, backup)
            finally:
                if os.path.exists(backup_temp_name):
                    os.unlink(backup_temp_name)

        os.replace(temporary_name, target)
        temporary_name = None
        _sync_directory(target.parent)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def save_application_config(path: str | Path, config: ApplicationConfig) -> None:
    if not isinstance(config, ApplicationConfig):
        raise TypeError("config must be an ApplicationConfig")
    atomic_write_json(path, config.to_dict())


def _read_config(path: Path) -> ApplicationConfig:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return ApplicationConfig.from_dict(data)


def _quarantine(path: Path) -> Path | None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    quarantine = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        shutil.copy2(path, quarantine)
    except OSError:
        return None
    return quarantine


def load_application_config(
    path: str | Path,
    *,
    default_factory: Callable[[], ApplicationConfig] = ApplicationConfig,
    recover_from_backup: bool = True,
) -> ApplicationConfig:
    """Load config, recovering from ``.bak`` while preserving corrupt evidence."""

    target = Path(path)
    if not target.exists():
        return default_factory()
    try:
        return _read_config(target)
    except (OSError, UnicodeError, json.JSONDecodeError, ConfigValidationError) as primary_error:
        quarantine = _quarantine(target)
        backup = target.with_suffix(target.suffix + ".bak")
        if recover_from_backup and backup.exists():
            try:
                recovered = _read_config(backup)
                atomic_write_json(target, recovered.to_dict(), create_backup=False)
                return recovered
            except (OSError, UnicodeError, json.JSONDecodeError, ConfigValidationError):
                pass
        raise ConfigCorruptionError(
            target,
            f"configuration is corrupt and no valid backup is available: {primary_error}",
            quarantine,
        ) from primary_error


class JsonFormatter(logging.Formatter):
    """One-JSON-object-per-line formatter suitable for ingestion and support logs."""

    _standard_fields = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        document: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._standard_fields and not key.startswith("_")
        }
        if extras:
            document["context"] = extras
        if record.exc_info:
            document["exception"] = self.formatException(record.exc_info)
        return json.dumps(document, ensure_ascii=True, default=str, separators=(",", ":"))


def setup_structured_logging(
    log_file: str | Path,
    *,
    level: str | int = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
    logger_name: str = "long_core_gui",
    propagate: bool = False,
) -> logging.Logger:
    """Configure one idempotent rotating JSON file handler for the application."""

    if max_bytes <= 0 or backup_count < 0:
        raise ValueError("invalid log rotation settings")
    path = Path(log_file).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = propagate

    marker = str(path)
    for handler in logger.handlers:
        if getattr(handler, "_long_core_log_path", None) == marker:
            handler.setLevel(level)
            return logger

    handler = RotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    handler._long_core_log_path = marker  # type: ignore[attr-defined]
    logger.addHandler(handler)
    return logger
