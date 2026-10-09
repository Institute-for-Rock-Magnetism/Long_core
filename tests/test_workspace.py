import csv
import json
from pathlib import Path
import tempfile
import unittest
from long_core_gui.domain import HomingPolicy
from long_core_gui.services.storage import WorkspaceRepository


class WorkspaceTests(unittest.TestCase):
    def test_recovery_preserves_corrupt_evidence_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = WorkspaceRepository(directory)
            original = [{"sample_id": "core1", "x": 1}]
            repo.save([], HomingPolicy.EVERY_QUEUE, original)
            repo.save([], HomingPolicy.EVERY_QUEUE, [])
            repo.state_path.write_text("broken", encoding="utf-8")
            self.assertEqual(repo.load()[2], original)
            self.assertEqual(len(list(Path(directory).glob("workspace.corrupt-*.json"))), 1)
            self.assertEqual(json.loads(repo.state_path.read_text())["results"], original)

    def test_empty_save_clears_stale_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = WorkspaceRepository(directory)
            repo.save([], HomingPolicy.EVERY_QUEUE, [{"sample_id": "core1"}])
            repo.save([], HomingPolicy.EVERY_QUEUE, [])
            with repo.results_path.open() as file:
                self.assertEqual(list(csv.DictReader(file)), [])

    def test_run_snapshot_isolated_from_other_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = WorkspaceRepository(directory)
            results = [{"run_id": "abc", "sample_id": "A"}, {"run_id": "def", "sample_id": "B"}]
            repo.save_run({"run_id": "abc", "state": "Completed", "started_at": "2026-01-01"}, results)
            self.assertEqual(repo.list_runs()[0]["results"], results[:1])
            with self.assertRaises(ValueError): repo.save_run({"run_id": "../bad"}, [])

    def test_invalid_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = WorkspaceRepository(directory)
            repo.state_path.write_text('{"schema_version": 1, "results": [4]}')
            with self.assertRaises(RuntimeError): repo.load()
