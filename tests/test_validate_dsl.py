from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from dify_dsl_validator import validate_document, validate_path  # noqa: E402


class ValidatorFixtureTests(unittest.TestCase):
    def test_valid_fixtures_have_no_errors(self) -> None:
        paths = sorted((FIXTURES / "valid").glob("*.yml"))
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            with self.subTest(path=path.name):
                report = validate_path(path)
                self.assertEqual([], report.errors, report.format_text())

    def test_invalid_fixtures_report_expected_codes(self) -> None:
        expected = {
            "agent-package-missing-ref.yml": {"agent.package-ref"},
            "bad-branch-handle.yml": {"edge.invalid-branch-handle"},
            "bad-human-input.yml": {"node.human-input.duplicate-action"},
            "cycle.yml": {"graph.cycle"},
            "disconnected.yml": {"graph.unreachable-node", "graph.unreachable-terminal"},
            "missing-dependency.yml": {"dependency.missing"},
            "unknown-output.yml": {"reference.unknown-output"},
            "unsupported-version.yml": {"version.unsupported"},
        }
        for name, codes in expected.items():
            with self.subTest(path=name):
                report = validate_path(FIXTURES / "invalid" / name)
                actual = {diagnostic.code for diagnostic in report.errors}
                self.assertTrue(codes <= actual, report.format_text())

    def test_sql_risks_are_reported_as_warnings(self) -> None:
        report = validate_path(FIXTURES / "warnings" / "unsafe-sql.yml")
        codes = {diagnostic.code for diagnostic in report.warnings}
        self.assertIn("sql.destructive", codes)
        self.assertIn("sql.interpolation", codes)
        self.assertIn("sql.multiple-statements", codes)

    def test_target_version_mismatch_is_an_error(self) -> None:
        report = validate_path(FIXTURES / "valid" / "workflow-0.6.yml", target_version="0.7.0")
        self.assertIn("version.target-mismatch", {diagnostic.code for diagnostic in report.errors})

    def test_json_report_is_machine_readable(self) -> None:
        report = validate_path(FIXTURES / "invalid" / "disconnected.yml")
        payload = report.as_dict()
        self.assertEqual("invalid", payload["status"])
        self.assertGreater(payload["summary"]["errors"], 0)
        json.dumps(payload)

    def test_cli_preserves_backwards_compatible_usage(self) -> None:
        command = [
            sys.executable,
            str(SCRIPTS / "validate_dsl.py"),
            str(FIXTURES / "valid" / "workflow-0.7.yml"),
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("OK", completed.stdout)

    def test_cli_strict_fails_on_warnings(self) -> None:
        command = [
            sys.executable,
            str(SCRIPTS / "validate_dsl.py"),
            "--strict",
            str(FIXTURES / "warnings" / "unsafe-sql.yml"),
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)

    def test_cli_json_output_and_exit_status(self) -> None:
        command = [
            sys.executable,
            str(SCRIPTS / "validate_dsl.py"),
            "--format",
            "json",
            str(FIXTURES / "invalid" / "cycle.yml"),
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual("invalid", payload["status"])
        self.assertIn("graph.cycle", {item["code"] for item in payload["diagnostics"]})

    def test_non_mapping_document_is_rejected(self) -> None:
        report = validate_document(["not", "an", "app"])
        self.assertIn("document.type", {diagnostic.code for diagnostic in report.errors})

    def test_malformed_yaml_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.yml"
            path.write_text("app: [\n", encoding="utf-8")
            report = validate_path(path)
        self.assertIn("yaml.parse", {diagnostic.code for diagnostic in report.errors})

    def test_agent_v2_is_rejected_for_0_6(self) -> None:
        document = {
            "version": "0.6.0",
            "kind": "app",
            "app": {"name": "Wrong version", "mode": "workflow"},
            "agent_packages": {
                "agent_1": {
                    "schema_version": 1,
                    "metadata": {"name": "Agent"},
                    "soul": {"schema_version": 1},
                    "omitted_assets": [],
                }
            },
            "dependencies": [],
            "workflow": {
                "graph": {
                    "nodes": [
                        {"id": "start", "type": "custom", "data": {"type": "start", "variables": []}},
                        {
                            "id": "agent",
                            "type": "custom",
                            "data": {
                                "type": "agent",
                                "version": "2",
                                "agent_node_kind": "dify_agent",
                                "agent_binding": {"binding_type": "inline_agent", "package_ref": "agent_1"},
                                "agent_job": {"schema_version": 1, "declared_outputs": []},
                            },
                        },
                        {"id": "end", "type": "custom", "data": {"type": "end", "outputs": []}},
                    ],
                    "edges": [
                        {
                            "id": "start-agent",
                            "source": "start",
                            "target": "agent",
                            "sourceHandle": "source",
                            "targetHandle": "target",
                            "data": {"sourceType": "start", "targetType": "agent"},
                        },
                        {
                            "id": "agent-end",
                            "source": "agent",
                            "target": "end",
                            "sourceHandle": "source",
                            "targetHandle": "target",
                            "data": {"sourceType": "agent", "targetType": "end"},
                        },
                    ],
                }
            },
        }
        codes = {diagnostic.code for diagnostic in validate_document(document).errors}
        self.assertIn("version.feature-agent-packages", codes)
        self.assertIn("version.feature-agent-v2", codes)

    def test_legacy_model_config_dependencies_are_checked(self) -> None:
        document = {
            "version": "0.6.0",
            "kind": "app",
            "app": {"name": "Legacy chat", "mode": "agent-chat"},
            "dependencies": [],
            "model_config": {
                "model": {
                    "provider": "acme/models/provider",
                    "name": "model",
                    "mode": "chat",
                }
            },
        }
        codes = {diagnostic.code for diagnostic in validate_document(document).errors}
        self.assertIn("dependency.missing", codes)


if __name__ == "__main__":
    unittest.main()
