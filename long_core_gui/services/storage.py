"""Workspace persistence for queues, measurement results, and probe captures."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..domain import HomingPolicy, QueuePlan, QueueStep
from ..infrastructure import atomic_write_json
from ..infrastructure.probe import ProbeCapture


class WorkspaceRepository:
    SCHEMA_VERSION = 1

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_path = self.directory / "workspace.json"
        self.results_path = self.directory / "measurements.csv"

    def load(self) -> tuple[list[QueueStep], HomingPolicy, list[dict[str, Any]]]:
        backup = self.state_path.with_suffix(".json.bak")
        errors = []
        for source in (self.state_path, backup):
            if not source.exists():
                continue
            try:
                data = json.loads(source.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or data.get("schema_version") != self.SCHEMA_VERSION:
                    raise ValueError("unsupported workspace schema")
                plan = QueuePlan.from_dict(data["plan"]) if data.get("plan") else None
                results = data.get("results", [])
                if not isinstance(results, list) or any(not isinstance(row, dict) for row in results):
                    raise ValueError("results must be a list of measurement objects")
                if source == backup:
                    if self.state_path.exists():
                        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
                        shutil.copy2(self.state_path, self.state_path.with_name(f"workspace.corrupt-{stamp}.json"))
                    atomic_write_json(self.state_path, data, create_backup=False)
                return (list(plan.steps), plan.homing, results) if plan else ([], HomingPolicy.EVERY_QUEUE, results)
            except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError("could not load workspace or backup: " + "; ".join(errors))
        return [], HomingPolicy.EVERY_QUEUE, []

    def save_run(self, record: dict[str, Any], results: list[dict[str, Any]] | None = None) -> None:
        run_id = record["run_id"]
        if not isinstance(run_id, str) or not run_id.isalnum():
            raise ValueError("invalid run ID")
        snapshot = dict(record)
        snapshot["results"] = [r for r in (results if results is not None else self.load()[2]) if r.get("run_id") == run_id]
        atomic_write_json(self.directory / "runs" / f"{run_id}.json", snapshot)

    def list_runs(self) -> list[dict[str, Any]]:
        records = []
        for path in (self.directory / "runs").glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(record, dict) and "run_id" in record:
                    records.append(record)
            except (OSError, ValueError):
                continue
        return sorted(records, key=lambda r: r.get("started_at", ""), reverse=True)

    def export_results(self, path: str | Path, results: list[dict[str, Any]]) -> None:
        self._write_results(results, Path(path))

    def save(
        self,
        steps: list[QueueStep],
        homing: HomingPolicy,
        results: list[dict[str, Any]],
    ) -> None:
        plan = QueuePlan(tuple(steps), homing).to_dict() if steps else None
        atomic_write_json(
            self.state_path,
            {"schema_version": self.SCHEMA_VERSION, "plan": plan, "results": results},
        )
        self._write_results(results)

    def export_plan(self, path: str | Path, plan: QueuePlan) -> None:
        atomic_write_json(path, plan.to_dict())

    def import_plan(self, path: str | Path) -> QueuePlan:
        try:
            return QueuePlan.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise RuntimeError(f"could not import queue: {exc}") from exc

    def _write_results(self, results: list[dict[str, Any]], path: Path | None = None) -> None:
        fields = [
            "sample_id", "daq_type", "instrument", "x", "y", "z",
            "intensity", "inclination", "declination", "sequence", "position_mm", "reading", "run_id", "timestamp",
            "geographic_inclination", "geographic_declination", "tilt_corrected_inclination", "tilt_corrected_declination",
        ]
        target = path or self.results_path
        temporary = target.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        temporary.replace(target)

    def save_probe_capture(self, capture: ProbeCapture) -> Path:
        """Persist one probe capture as JSON under ``probes/`` in the workspace."""
        if not isinstance(capture, ProbeCapture):
            raise TypeError("capture must be a ProbeCapture")
        probes = self.directory / "probes"
        probes.mkdir(parents=True, exist_ok=True)
        stamp = capture.started_at.replace(":", "-").replace("+00:00", "Z")
        target = probes / f"{stamp}_{capture.subsystem}.json"
        atomic_write_json(target, capture.to_dict())
        return target
