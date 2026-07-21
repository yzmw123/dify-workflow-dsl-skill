from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from dify_dsl_validator import validate_document, validate_path  # noqa: E402
from dify_dsl_validator.validator import Validator  # noqa: E402


def load_fixture(*parts: str) -> dict[str, object]:
    path = FIXTURES.joinpath(*parts)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def base_workflow_document() -> dict[str, object]:
    return {
        "version": "0.7.0",
        "kind": "app",
        "app": {"name": "Base", "mode": "workflow"},
        "dependencies": [],
        "workflow": {
            "conversation_variables": [{"name": "target", "value_type": "string", "value": ""}],
            "environment_variables": [],
            "graph": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "custom",
                        "data": {
                            "type": "start",
                            "title": "Start",
                            "variables": [
                                {
                                    "label": "Input",
                                    "variable": "input_text",
                                    "type": "paragraph",
                                    "required": True,
                                }
                            ],
                        },
                    },
                    {"id": "end", "type": "custom", "data": {"type": "end", "title": "End", "outputs": []}},
                ],
                "edges": [
                    {
                        "id": "start-end",
                        "source": "start",
                        "target": "end",
                        "sourceHandle": "source",
                        "targetHandle": "target",
                        "data": {"sourceType": "start", "targetType": "end"},
                    }
                ],
            },
        },
    }


class ValidatorFixtureTests(unittest.TestCase):
    def test_valid_fixtures_have_no_diagnostics(self) -> None:
        paths = sorted((FIXTURES / "valid").glob("*.yml"))
        paths.extend(sorted((FIXTURES / "valid-0.6").glob("*.yml")))
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            with self.subTest(path=path.name):
                report = validate_path(path)
                self.assertEqual([], report.errors, report.format_text())
                self.assertEqual([], report.warnings, report.format_text())

    def test_invalid_fixtures_report_expected_codes(self) -> None:
        expected = {
            "agent-declared-output-missing-type.yml": {"node.agent-v2.declared-output-type"},
            "agent-package-unknown-field.yml": {"agent.package-extra-field"},
            "agent-package-missing-ref.yml": {"agent.package-ref"},
            "assigner-unknown-value.yml": {"reference.unknown-root"},
            "bad-branch-handle.yml": {"edge.invalid-branch-handle"},
            "bad-human-input.yml": {"node.human-input.duplicate-action"},
            "cycle.yml": {"graph.cycle"},
            "dangling-container.yml": {"container.reference"},
            "disconnected.yml": {"graph.unreachable-node", "graph.unreachable-terminal"},
            "empty-iteration.yml": {"container.empty"},
            "human-select-missing-option-source.yml": {"node.human-input.option-source"},
            "llm-missing-context.yml": {"node.llm.context"},
            "missing-dependency.yml": {"dependency.missing"},
            "template-invalid-node-id.yml": {"reference.template-node-id"},
            "unknown-output.yml": {"reference.unknown-output"},
            "unsupported-version.yml": {"version.unsupported"},
        }
        for name, codes in expected.items():
            with self.subTest(path=name):
                report = validate_path(FIXTURES / "invalid" / name)
                actual = {diagnostic.code for diagnostic in report.errors}
                self.assertTrue(codes <= actual, report.format_text())

    def test_dify_1_16_scenarios_have_no_diagnostics(self) -> None:
        paths = sorted((ROOT / "examples" / "dify-1.16.0").glob("*.yml"))
        self.assertEqual(10, len(paths))
        for path in paths:
            with self.subTest(path=path.name):
                report = validate_path(path, target_version="0.7.0")
                self.assertEqual([], report.errors, report.format_text())
                self.assertEqual([], report.warnings, report.format_text())

    def test_sql_risks_are_reported_as_warnings(self) -> None:
        report = validate_path(FIXTURES / "warnings" / "unsafe-sql.yml")
        codes = {diagnostic.code for diagnostic in report.warnings}
        self.assertIn("sql.destructive", codes)
        self.assertIn("sql.interpolation", codes)
        self.assertIn("sql.multiple-statements", codes)

    def test_branch_risks_are_reported_as_warnings(self) -> None:
        expected = {
            "duplicate-branch-handle.yml": "graph.duplicate-branch-handle",
            "unconnected-branch.yml": "graph.unconnected-branch",
        }
        for name, code in expected.items():
            with self.subTest(path=name):
                report = validate_path(FIXTURES / "warnings" / name)
                self.assertEqual([], report.errors, report.format_text())
                self.assertIn(code, {diagnostic.code for diagnostic in report.warnings})

    def test_target_version_mismatch_is_an_error(self) -> None:
        report = validate_path(FIXTURES / "valid-0.6" / "workflow-0.6.yml", target_version="0.7.0")
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

    def test_unhashable_yaml_field_values_never_escape_as_exceptions(self) -> None:
        cases: list[tuple[str, dict[str, object], str]] = []

        document = base_workflow_document()
        document["workflow"]["graph"]["nodes"][0]["type"] = []
        cases.append(("wrapper type", document, "node.wrapper-type"))

        document = base_workflow_document()
        document["workflow"]["graph"]["nodes"][0]["data"]["variables"][0]["variable"] = []
        cases.append(("start variable", document, "node.start.variable"))

        document = base_workflow_document()
        document["workflow"]["conversation_variables"][0]["name"] = []
        cases.append(("workflow variable", document, "workflow.variable-field"))

        for field in ("source", "target"):
            document = base_workflow_document()
            document["workflow"]["graph"]["edges"][0][field] = []
            cases.append((f"edge {field}", document, "edge.endpoint-type"))

        document = base_workflow_document()
        document["workflow"]["graph"]["edges"][0]["sourceHandle"] = []
        cases.append(("edge sourceHandle", document, "edge.handle-type"))

        document = base_workflow_document()
        document["dependencies"] = [{"type": [], "value": {}}]
        cases.append(("dependency type", document, "dependency.unsupported-type"))

        human_base = load_fixture("valid", "human-input-0.7.yml")
        for label, path, code in (
            ("human input type", ("inputs", 0, "type"), "node.human-input.input-type"),
            ("human action id", ("user_actions", 0, "id"), "node.human-input.action-id"),
            ("human button style", ("user_actions", 0, "button_style"), "node.human-input.button-style"),
            ("human timeout unit", ("timeout_unit",), "node.human-input.timeout-unit"),
        ):
            document = copy.deepcopy(human_base)
            human = document["workflow"]["graph"]["nodes"][1]["data"]
            target: object = human
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = []
            cases.append((label, document, code))

        document = load_fixture("valid", "agent-v2-workflow-0.7.yml")
        document["workflow"]["graph"]["nodes"][1]["data"]["agent_binding"]["binding_type"] = []
        cases.append(("agent binding type", document, "node.agent-v2.binding-type"))

        document = load_fixture("valid", "agent-app-0.7.yml")
        document["agent_packages"]["agent_1"]["omitted_assets"] = [{"kind": [], "name": "asset"}]
        cases.append(("omitted asset kind", document, "agent.omitted-asset"))

        for label, document, expected_code in cases:
            with self.subTest(field=label):
                parsed = yaml.safe_load(yaml.safe_dump(document, sort_keys=False))
                report = validate_document(parsed)
                codes = {diagnostic.code for diagnostic in report.diagnostics}
                self.assertIn(expected_code, codes, report.format_text())
                self.assertNotIn("validator.internal", codes, report.format_text())

    def test_cli_batch_continues_after_invalid_field_types(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad_path = Path(directory) / "bad.yml"
            bad_path.write_text(
                yaml.safe_dump(
                    {
                        **base_workflow_document(),
                        "workflow": {
                            **base_workflow_document()["workflow"],
                            "graph": {
                                **base_workflow_document()["workflow"]["graph"],
                                "nodes": [
                                    {
                                        **base_workflow_document()["workflow"]["graph"]["nodes"][0],
                                        "type": [],
                                    },
                                    base_workflow_document()["workflow"]["graph"]["nodes"][1],
                                ],
                            },
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(SCRIPTS / "validate_dsl.py"),
                str(bad_path),
                str(FIXTURES / "valid" / "workflow-0.7.yml"),
            ]
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("node.wrapper-type", completed.stdout)
        self.assertIn("workflow-0.7.yml", completed.stdout)
        self.assertIn("OK", completed.stdout)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def test_system_selector_forms_and_plain_string_arrays_are_not_references(self) -> None:
        document = load_fixture("valid", "advanced-chat-0.7.yml")
        document["workflow"]["conversation_variables"] = [
            {
                "name": "choices",
                "value_type": "array[string]",
                "value": ["approve", "reject"],
            }
        ]
        document["workflow"]["features"] = {
            "file_upload": {
                "image": {
                    "transfer_methods": ["remote_url", "local_file"],
                }
            }
        }
        start_data = document["workflow"]["graph"]["nodes"][0]["data"]
        start_data["variables"] = [
            {
                "label": "Choice",
                "variable": "choice",
                "type": "select",
                "options": ["missing-node", "output"],
                "allowed_file_types": ["missing-node", "output"],
                "allowed_file_extensions": ["missing-node", "output"],
            }
        ]
        llm_data = document["workflow"]["graph"]["nodes"][1]["data"]
        llm_data["query_variable_selector"] = ["start", "sys.query"]
        llm_data["secondary_selector"] = ["sys", "query"]
        llm_data["dataset_ids"] = ["missing-node", "output"]
        llm_data["conditions"] = [
            {"comparison_operator": "in", "value": ["missing-node", "output"]}
        ]
        report = validate_document(document)
        self.assertEqual([], report.diagnostics, report.format_text())

        human = load_fixture("valid", "human-input-0.7.yml")
        human["workflow"]["graph"]["nodes"][1]["data"]["inputs"].append(
            {
                "type": "select",
                "output_variable_name": "decision",
                "option_source": {
                    "type": "constant",
                    "selector": [],
                    "value": ["approve", "reject"],
                },
            }
        )
        report = validate_document(human)
        self.assertEqual([], report.diagnostics, report.format_text())

    def test_dify_container_start_helpers_and_internal_outputs_are_valid(self) -> None:
        def edge(edge_id: str, source: str, target: str, source_type: str, target_type: str) -> dict[str, object]:
            return {
                "id": edge_id,
                "source": source,
                "target": target,
                "sourceHandle": "source",
                "targetHandle": "target",
                "data": {"sourceType": source_type, "targetType": target_type},
            }

        iteration = base_workflow_document()
        iteration["workflow"]["graph"] = {
            "nodes": [
                {
                    "id": "start",
                    "type": "custom",
                    "data": {
                        "type": "start",
                        "variables": [
                            {
                                "label": "Items",
                                "variable": "items",
                                "type": "paragraph",
                                "required": True,
                            }
                        ],
                    },
                },
                {
                    "id": "iteration",
                    "type": "custom",
                    "data": {
                        "type": "iteration",
                        "start_node_id": "iteration_start",
                        "iterator_selector": ["start", "items"],
                        "output_selector": ["iteration_child", "result"],
                    },
                },
                {
                    "id": "iteration_start",
                    "type": "custom-iteration-start",
                    "parentId": "iteration",
                    "data": {"type": "iteration-start", "isInIteration": True},
                },
                {
                    "id": "iteration_child",
                    "type": "custom",
                    "parentId": "iteration",
                    "data": {
                        "type": "code",
                        "isInIteration": True,
                        "iteration_id": "iteration",
                        "code_language": "python3",
                        "code": "def main(item, index):\n    return {'result': item}\n",
                        "variables": [
                            {"variable": "item", "value_selector": ["iteration", "item"]},
                            {"variable": "index", "value_selector": ["iteration", "index"]},
                        ],
                        "outputs": {"result": {"type": "string"}},
                    },
                },
                {
                    "id": "end",
                    "type": "custom",
                    "data": {
                        "type": "end",
                        "outputs": [{"variable": "result", "value_selector": ["iteration", "output"]}],
                    },
                },
            ],
            "edges": [
                edge("start-iteration", "start", "iteration", "start", "iteration"),
                edge("iteration-end", "iteration", "end", "iteration", "end"),
                edge(
                    "iteration-start-child",
                    "iteration_start",
                    "iteration_child",
                    "iteration-start",
                    "code",
                ),
            ],
        }

        loop = base_workflow_document()
        loop["workflow"]["graph"] = {
            "nodes": [
                {"id": "start", "type": "custom", "data": {"type": "start", "variables": []}},
                {
                    "id": "loop",
                    "type": "custom",
                    "data": {
                        "type": "loop",
                        "start_node_id": "loop_start",
                        "loop_count": 10,
                        "loop_variables": [
                            {
                                "id": "counter",
                                "label": "num",
                                "value": "1",
                                "value_type": "constant",
                                "var_type": "number",
                            }
                        ],
                    },
                },
                {
                    "id": "loop_start",
                    "type": "custom-loop-start",
                    "parentId": "loop",
                    "data": {"type": "loop-start", "isInLoop": True},
                },
                {
                    "id": "loop_child",
                    "type": "custom",
                    "parentId": "loop",
                    "data": {
                        "type": "assigner",
                        "version": "2",
                        "isInLoop": True,
                        "loop_id": "loop",
                        "items": [
                            {
                                "variable_selector": ["loop", "num"],
                                "input_type": "constant",
                                "operation": "+=",
                                "value": 1,
                            }
                        ],
                    },
                },
                {
                    "id": "end",
                    "type": "custom",
                    "data": {
                        "type": "end",
                        "outputs": [{"variable": "result", "value_selector": ["loop", "output"]}],
                    },
                },
            ],
            "edges": [
                edge("start-loop", "start", "loop", "start", "loop"),
                edge("loop-end", "loop", "end", "loop", "end"),
                edge("loop-start-child", "loop_start", "loop_child", "loop-start", "assigner"),
            ],
        }

        for label, document in (("iteration", iteration), ("loop", loop)):
            with self.subTest(container=label):
                report = validate_document(document)
                self.assertEqual([], report.diagnostics, report.format_text())

    def test_nested_selector_collections_still_report_unknown_references(self) -> None:
        document = base_workflow_document()
        document["workflow"]["graph"]["nodes"].insert(
            1,
            {
                "id": "aggregate",
                "type": "custom",
                "data": {
                    "type": "variable-aggregator",
                    "title": "Aggregate",
                    "variables": [["missing-node", "output"]],
                },
            },
        )
        document["workflow"]["graph"]["edges"] = [
            {
                "id": "start-aggregate",
                "source": "start",
                "target": "aggregate",
                "sourceHandle": "source",
                "targetHandle": "target",
                "data": {"sourceType": "start", "targetType": "variable-aggregator"},
            },
            {
                "id": "aggregate-end",
                "source": "aggregate",
                "target": "end",
                "sourceHandle": "source",
                "targetHandle": "target",
                "data": {"sourceType": "variable-aggregator", "targetType": "end"},
            },
        ]

        report = validate_document(document)
        self.assertIn("reference.unknown-root", {diagnostic.code for diagnostic in report.errors})

    def test_agent_soul_nested_import_constraints_are_rejected(self) -> None:
        document = load_fixture("valid", "agent-app-0.7.yml")
        soul = document["agent_packages"]["agent_1"]["soul"]
        soul["knowledge"] = {"unknown": True}
        soul["model"] = {}
        soul["config_skills"] = [
            {
                "name": "Bad Skill Name",
                "file_kind": "tool_file",
                "file_id": "",
                "is_missing": False,
                "unknown": True,
            }
        ]
        soul["config_files"] = [
            {
                "name": "file.txt",
                "file_kind": "invalid",
                "file_id": "",
                "is_missing": False,
            }
        ]

        report = validate_document(document)
        codes = {diagnostic.code for diagnostic in report.errors}
        locations = {diagnostic.location for diagnostic in report.errors}
        self.assertIn("agent.soul-extra-field", codes)
        self.assertIn("agent.soul-field-type", codes)
        self.assertIn("agent_packages.agent_1.soul.knowledge.unknown", locations)
        self.assertIn("agent_packages.agent_1.soul.model.plugin_id", locations)
        self.assertIn("agent_packages.agent_1.soul.config_skills[0].unknown", locations)
        self.assertIn("agent_packages.agent_1.soul.config_files[0].file_kind", locations)

    def test_valid_agent_soul_nested_config_has_no_diagnostics(self) -> None:
        document = load_fixture("valid", "agent-app-0.7.yml")
        document["dependencies"] = [
            {
                "type": "marketplace",
                "value": {
                    "marketplace_plugin_unique_identifier": "langgenius/openai:1.0.0",
                },
            }
        ]
        soul = document["agent_packages"]["agent_1"]["soul"]
        soul.update(
            {
                "knowledge": {
                    "sets": [
                        {
                            "id": "primary",
                            "name": "Primary",
                            "datasets": [{"id": "dataset-1"}],
                            "query": {"mode": "user_query"},
                            "retrieval": {"mode": "multiple", "top_k": 5},
                        }
                    ]
                },
                "model": {
                    "plugin_id": "langgenius/openai",
                    "model_provider": "langgenius/openai/openai",
                    "model": "gpt-4o-mini",
                    "credential_ref": None,
                    "model_settings": {},
                },
                "config_skills": [
                    {
                        "name": "review-skill",
                        "file_kind": "tool_file",
                        "file_id": "",
                        "is_missing": True,
                    }
                ],
                "config_files": [
                    {
                        "name": "guide.txt",
                        "file_kind": "upload_file",
                        "file_id": "",
                        "is_missing": True,
                    }
                ],
            }
        )

        report = validate_document(document)
        self.assertEqual([], report.diagnostics, report.format_text())

    def test_declared_output_check_and_failure_strategy_constraints_are_rejected(self) -> None:
        cases = {
            "check-extra": {
                "name": "result",
                "type": "string",
                "check": {"enabled": False, "unknown": True},
            },
            "enabled-check-missing-fields": {
                "name": "result",
                "type": "file",
                "check": {"enabled": True},
            },
            "missing-default": {
                "name": "result",
                "type": "string",
                "failure_strategy": {"on_failure": "default_value"},
            },
            "wrong-default-type": {
                "name": "result",
                "type": "number",
                "failure_strategy": {
                    "on_failure": "default_value",
                    "default_value": "not-a-number",
                },
            },
            "invalid-retry": {
                "name": "result",
                "type": "string",
                "failure_strategy": {
                    "retry": {
                        "enabled": True,
                        "max_retries": 11,
                        "retry_interval_ms": -1,
                        "unknown": True,
                    }
                },
            },
        }
        for label, declared_output in cases.items():
            with self.subTest(case=label):
                document = load_fixture("valid", "agent-v2-workflow-0.7.yml")
                job = document["workflow"]["graph"]["nodes"][1]["data"]["agent_job"]
                job["declared_outputs"] = [declared_output]
                document["workflow"]["graph"]["nodes"][2]["data"]["outputs"][0]["value_selector"] = [
                    "worker",
                    "result",
                ]
                report = validate_document(document)
                codes = {diagnostic.code for diagnostic in report.errors}
                self.assertTrue(
                    {
                        "node.agent-v2.declared-output-extra-field",
                        "node.agent-v2.declared-output-shape",
                    }
                    & codes,
                    report.format_text(),
                )

    def test_valid_declared_output_check_and_failure_strategy_have_no_errors(self) -> None:
        document = load_fixture("valid", "agent-v2-workflow-0.7.yml")
        job = document["workflow"]["graph"]["nodes"][1]["data"]["agent_job"]
        job["declared_outputs"] = [
            {
                "name": "report",
                "type": "file",
                "check": {
                    "enabled": True,
                    "prompt": "Compare the generated report with the benchmark.",
                    "benchmark_file_ref": {
                        "reference": "dify-file-ref:example",
                        "transfer_method": "tool_file",
                    },
                },
                "failure_strategy": {
                    "retry": {
                        "enabled": True,
                        "max_retries": 2,
                        "retry_interval_ms": 1000,
                    },
                    "on_failure": "fail_branch",
                },
            }
        ]
        document["workflow"]["graph"]["nodes"][2]["data"]["outputs"][0]["value_selector"] = [
            "worker",
            "report",
        ]

        report = validate_document(document)
        self.assertEqual([], report.errors, report.format_text())

    def test_agent_package_nested_constraints_have_stable_codes(self) -> None:
        document = load_fixture("valid", "agent-app-0.7.yml")
        package = document["agent_packages"]["agent_1"]
        package["metadata"]["name"] = "x" * 256
        package["metadata"]["description"] = []
        package["metadata"]["unknown"] = True
        package["soul"]["unknown"] = True
        package["soul"]["prompt"] = []
        package["omitted_assets"] = [
            {"kind": "skill", "name": "asset", "size": [], "unknown": True}
        ]
        codes = {diagnostic.code for diagnostic in validate_document(document).errors}
        self.assertIn("agent.package-metadata", codes)
        self.assertIn("agent.package-metadata-field", codes)
        self.assertIn("agent.package-extra-field", codes)
        self.assertIn("agent.soul-extra-field", codes)
        self.assertIn("agent.soul-field-type", codes)
        self.assertIn("agent.omitted-asset-field", codes)

    def test_agent_job_and_declared_output_constraints_have_stable_codes(self) -> None:
        document = load_fixture("valid", "agent-v2-workflow-0.7.yml")
        job = document["workflow"]["graph"]["nodes"][1]["data"]["agent_job"]
        job["unknown"] = True
        job["mode"] = []
        job["declared_outputs"] = [
            {
                "name": "bad-name",
                "type": "array",
                "array_item": {"type": "array"},
                "children": [{"name": "child", "type": "string"}],
                "unknown": True,
            },
            [],
        ]
        codes = {diagnostic.code for diagnostic in validate_document(document).errors}
        self.assertIn("node.agent-v2.job-extra-field", codes)
        self.assertIn("node.agent-v2.job-field", codes)
        self.assertIn("node.agent-v2.declared-output", codes)
        self.assertIn("node.agent-v2.declared-output-extra-field", codes)
        self.assertIn("node.agent-v2.declared-output-name", codes)
        self.assertIn("node.agent-v2.declared-output-shape", codes)

    def test_human_input_value_sources_and_file_constraints_have_stable_codes(self) -> None:
        document = load_fixture("valid", "human-input-0.7.yml")
        human = document["workflow"]["graph"]["nodes"][1]["data"]
        human["inputs"] = [
            {
                "type": "paragraph",
                "output_variable_name": "comment",
                "default": {"type": "variable", "selector": ["start"], "value": ""},
            },
            {
                "type": "select",
                "output_variable_name": "choice",
                "option_source": {"type": "variable", "selector": ["start"], "value": []},
            },
            {
                "type": "file",
                "output_variable_name": "attachment",
                "allowed_file_types": ["custom"],
                "allowed_file_extensions": [],
                "allowed_file_upload_methods": ["tool_file"],
            },
            {
                "type": "file-list",
                "output_variable_name": "attachments",
                "allowed_file_types": ["image"],
                "allowed_file_extensions": [],
                "allowed_file_upload_methods": ["local_file"],
                "number_limits": -1,
            },
        ]
        codes = {diagnostic.code for diagnostic in validate_document(document).errors}
        self.assertIn("node.human-input.default", codes)
        self.assertIn("node.human-input.option-source", codes)
        self.assertIn("node.human-input.file-config", codes)

    def test_all_branch_node_kinds_report_unconnected_declared_handles(self) -> None:
        classifier = load_fixture("warnings", "unconnected-branch.yml")
        branch = classifier["workflow"]["graph"]["nodes"][1]["data"]
        branch["type"] = "question-classifier"
        branch.pop("cases")
        branch["classes"] = [{"id": "one", "name": "One"}, {"id": "two", "name": "Two"}]
        classifier["workflow"]["graph"]["edges"][0]["data"]["targetType"] = "question-classifier"
        classifier_edge = classifier["workflow"]["graph"]["edges"][1]
        classifier_edge["sourceHandle"] = "one"
        classifier_edge["data"]["sourceType"] = "question-classifier"

        human = load_fixture("valid", "human-input-0.7.yml")
        human["workflow"]["graph"]["nodes"][1]["data"]["user_actions"].append(
            {"id": "reject", "title": "Reject", "button_style": "default"}
        )

        for label, document in (("question-classifier", classifier), ("human-input", human)):
            with self.subTest(node_type=label):
                report = validate_document(document)
                self.assertEqual([], report.errors, report.format_text())
                self.assertIn(
                    "graph.unconnected-branch",
                    {diagnostic.code for diagnostic in report.warnings},
                )

    def test_container_start_and_parent_constraints_have_stable_codes(self) -> None:
        document = load_fixture("invalid", "empty-iteration.yml")
        document["workflow"]["graph"]["nodes"][2]["parentId"] = "start"
        codes = {diagnostic.code for diagnostic in validate_document(document).errors}
        self.assertIn("container.reference", codes)
        self.assertIn("container.start-node", codes)
        self.assertIn("container.empty", codes)

    def test_reachable_non_terminal_without_outgoing_edge_is_a_warning(self) -> None:
        document = base_workflow_document()
        document["workflow"]["graph"]["nodes"].append(
            {
                "id": "dead",
                "type": "custom",
                "data": {
                    "type": "code",
                    "title": "Dead",
                    "code_language": "python3",
                    "code": "def main():\n    return {'result': 'ok'}\n",
                    "outputs": {"result": {"type": "string"}},
                },
            }
        )
        document["workflow"]["graph"]["edges"].append(
            {
                "id": "start-dead",
                "source": "start",
                "target": "dead",
                "sourceHandle": "source",
                "targetHandle": "target",
                "data": {"sourceType": "start", "targetType": "code"},
            }
        )
        report = validate_document(document)
        self.assertEqual([], report.errors, report.format_text())
        self.assertIn("graph.dead-end", {diagnostic.code for diagnostic in report.warnings})

    def test_internal_exception_boundary_returns_a_diagnostic(self) -> None:
        with mock.patch.object(Validator, "_validate_header", side_effect=RuntimeError("boom")):
            report = validate_document(base_workflow_document())
        self.assertIn("validator.internal", {diagnostic.code for diagnostic in report.errors})


if __name__ == "__main__":
    unittest.main()
