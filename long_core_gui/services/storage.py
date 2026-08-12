"""Workspace persistence for queues, measurement results, and probe captures."""

from __future__ import annotations

import csv
import json
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
        if not self.state_path.exists():
            return [], HomingPolicy.EVERY_QUEUE, []
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if data.get("schema_version") != self.SCHEMA_VERSION:
                raise ValueError("unsupported workspace schema")
            plan_data = data.get("plan")
            if plan_data:
                plan = QueuePlan.from_dict(plan_data)
                steps, homing = list(plan.steps), plan.homing
            else:
                steps, homing = [], HomingPolicy.EVERY_QUEUE
            results = data.get("results", [])
            if not isinstance(results, list):
                raise ValueError("results must be a list")
            return steps, homing, results
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise RuntimeError(f"could not load workspace: {exc}") from exc

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

    def _write_results(self, results: list[dict[str, Any]]) -> None:
        if not results:
            return
        fields = [
            "sample_id", "daq_type", "instrument", "x", "y", "z",
            "intensity", "inclination", "declination", "sequence",
        ]
        temporary = self.results_path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        temporary.replace(self.results_path)

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
