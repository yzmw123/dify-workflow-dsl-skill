from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from dify_dsl_validator import validate_document, validate_path


def example(name):
    return yaml.safe_load((ROOT / "examples" / "dify-1.18.0" / name).read_text())


def agent(document):
    return next(n["data"] for n in document["workflow"]["graph"]["nodes"] if n["data"]["type"] == "agent")


class Dify118Tests(unittest.TestCase):
    def assert_code(self, document, code, target="1.18"):
        report = validate_document(document, dify_version=target)
        self.assertNotIn("validator.internal", {d.code for d in report.errors}, report.format_text())
        self.assertIn(code, {d.code for d in report.errors}, report.format_text())

    def test_versioned_examples(self):
        for folder, target in (("dify-1.16.0", "1.16"), ("dify-1.16.0", "1.18"), ("dify-1.18.0", "1.18")):
            for path in (ROOT / "examples" / folder).glob("*.yml"):
                with self.subTest(target=target, file=path.name):
                    report = validate_path(path, dify_version=target)
                    self.assertEqual([], report.diagnostics, report.format_text())

    def test_version_selection_and_default(self):
        doc = example("01-agent-text.yml")
        self.assertEqual("1.18", validate_document(doc).dify_version)
        self.assertEqual("1.18", validate_document(doc, dify_version="1.18.0").dify_version)
        self.assert_code(doc, "version.dify-unsupported", "1.19")
        self.assert_code(doc, "version.dify-mismatch", "1.15")
        path = ROOT / "tests/fixtures/valid-0.6/workflow-0.6.yml"
        self.assertEqual([], validate_path(path, dify_version="1.15.0").diagnostics)
        self.assertEqual("1.15", validate_path(path).dify_version)

    def test_new_agent_fields_rejected_for_legacy_target(self):
        self.assert_code(example("02-agent-routes.yml"), "node.agent-v2.job-extra-field", "1.16")
        self.assert_code(example("03-agent-knowledge-skills.yml"), "agent.package-extra-field", "1.16")
        self.assert_code(example("03-agent-knowledge-skills.yml"), "agent.soul-extra-field", "1.16")
        self.assert_code(example("04-knowledge-retrieval-v2.yml"), "version.feature-knowledge-v2", "1.16")

    def test_system_outputs_and_legacy_outputs(self):
        doc = example("01-agent-text.yml")
        end = next(n["data"] for n in doc["workflow"]["graph"]["nodes"] if n["data"]["type"] == "end")
        end["outputs"][0]["value_selector"][-1] = "files"
        self.assert_code(doc, "reference.unknown-output")
        self.assertFalse(validate_document(doc, dify_version="1.16").errors)
        doc = example("02-agent-routes.yml")
        for reserved in ("text", "switch", "_session"):
            with self.subTest(reserved=reserved):
                changed = copy.deepcopy(doc)
                agent(changed)["agent_job"]["declared_outputs"].append({"name": reserved, "type": "string"})
                self.assert_code(changed, "node.agent-v2.reserved-output")
        agent(doc)["agent_job"]["declared_outputs"].append({"name": "obj", "type": "object", "children": [{"name": "text", "type": "string"}]})
        self.assertEqual([], validate_document(doc).diagnostics)

    def test_route_rules(self):
        base = example("02-agent-routes.yml")
        for value in (None, [], {"enabled": "yes"}, {"enabled": True, "routes": []},
                      {"enabled": True, "routes": [{"id": "source", "name": "a"}, {"id": "b", "name": ""}]},
                      {"routes": [{"id": "a"}, {"id": "a"}]}, {"routes": [3]},
                      {"routes": [{"id": [], "name": []}]}, {"unexpected": True}):
            with self.subTest(value=value):
                doc = copy.deepcopy(base)
                agent(doc)["agent_job"]["output_routes"] = value
                self.assert_code(doc, "node.agent-v2.routes")
        doc = copy.deepcopy(base)
        del agent(doc)["agent_output_routes"]
        self.assert_code(doc, "node.agent-v2.routes-mismatch")
        doc = copy.deepcopy(base)
        agent(doc)["error_strategy"] = "default-value"
        self.assert_code(doc, "node.agent-v2.routes-error-strategy")

    def test_route_edges_and_coverage(self):
        doc = example("02-agent-routes.yml")
        edge = next(e for e in doc["workflow"]["graph"]["edges"] if e["sourceHandle"] == "resolve")
        edge["sourceHandle"] = "source"
        self.assert_code(doc, "edge.invalid-branch-handle")
        self.assertIn("graph.unconnected-branch", {d.code for d in validate_document(doc).warnings})
        edge["sourceHandle"] = "fail-branch"
        self.assert_code(doc, "edge.invalid-branch-handle")
        agent(doc)["error_strategy"] = "fail-branch"
        self.assertNotIn("edge.invalid-branch-handle", {d.code for d in validate_document(doc).errors})

    def test_disabled_routes_reject_stale_route_edges(self):
        doc = example("02-agent-routes.yml")
        agent(doc)["agent_output_routes"]["enabled"] = False
        agent(doc)["agent_job"]["output_routes"]["enabled"] = False
        for node in doc["workflow"]["graph"]["nodes"]:
            if node["data"]["type"] == "end":
                node["data"]["outputs"] = [o for o in node["data"]["outputs"]
                                             if o["value_selector"][-1] != "switch"]
        self.assert_code(doc, "edge.invalid-branch-handle")
        for edge in doc["workflow"]["graph"]["edges"]:
            if edge["data"]["sourceType"] == "agent":
                edge["sourceHandle"] = "source"
        self.assertEqual([], validate_document(doc).diagnostics)

    def test_legacy_strategy_version_two(self):
        base = yaml.safe_load((ROOT / "tests/fixtures/valid-0.6/legacy-agent-0.6.yml").read_text())
        agent(base)["version"] = "2"
        for target, version in (("1.15", "0.6.0"), ("1.16", "0.7.0"), ("1.18", "0.7.0")):
            with self.subTest(target=target):
                doc = copy.deepcopy(base)
                doc["version"] = version
                self.assertEqual([], validate_document(doc, dify_version=target).diagnostics)
        # A damaged portable node must still produce an identity error.
        doc = example("01-agent-text.yml")
        del agent(doc)["agent_node_kind"]
        self.assert_code(doc, "node.agent-v2.identity")

    def test_missing_asset_null_ids_follow_118_normalization(self):
        for field, name, kind in (("config_files", "guide.txt", "upload_file"),
                                  ("config_skills", "support-guide", "tool_file")):
            with self.subTest(field=field):
                doc = example("01-agent-text.yml")
                asset = {"name": name, "file_kind": kind, "file_id": None, "is_missing": True}
                next(iter(doc["agent_packages"].values()))["soul"][field] = [asset]
                self.assertEqual([], validate_document(doc).diagnostics)
                self.assertIsNone(asset["file_id"], "Validation must not mutate the document")
                self.assert_code(doc, "agent.soul-field-type", "1.16")
                asset["is_missing"] = False
                self.assert_code(doc, "agent.soul-field-type")

    def test_workspace_skill_constraints(self):
        for value in (None, {}, [None], [{"name": "x"}], [{"name": "x", "priority": -1}],
                      [{"name": "x", "priority": True}], [{"name": "x", "priority": 0, "unknown": 1}]):
            doc = example("03-agent-knowledge-skills.yml")
            next(iter(doc["agent_packages"].values()))["workspace_skills"] = value
            self.assert_code(doc, "agent.workspace-skills")

    def test_knowledge_space_constraints(self):
        base = example("03-agent-knowledge-skills.yml")
        package = next(iter(base["agent_packages"].values()))
        space = package["soul"]["knowledge"]["spaces"][0]
        for value in (None, {}, [None], [{}], [dict(space, control_space_id="invalid")],
                      [dict(space, id="\n")], [dict(space, is_missing=[])], [space, space],
                      [dict(space, description="x" * 2001)], [dict(space, extra=1)]):
            doc = copy.deepcopy(base)
            next(iter(doc["agent_packages"].values()))["soul"]["knowledge"]["spaces"] = value
            self.assert_code(doc, "agent.knowledge-spaces")

    def test_retrieval_and_site_validation(self):
        base = example("04-knowledge-retrieval-v2.yml")
        for key, value in (("control_space_ids", []), ("top_n", 101), ("top_n", True),
                           ("query_variable_selector", []), ("query_variable_selector", ["x"]),
                           ("score_threshold", 2), ("mode", [])):
            doc = copy.deepcopy(base)
            node = next(n["data"] for n in doc["workflow"]["graph"]["nodes"] if n["data"]["type"] == "knowledge-retrieval-v2")
            node[key] = value
            self.assert_code(doc, "node.knowledge-v2.config")
        for site in ([], {"title": None}, {"show_workflow_steps": "yes"}, {"token_strategy": "public"}):
            doc = copy.deepcopy(base)
            doc["site"] = site
            self.assert_code(doc, "site.config")

    def test_package_and_non_utf8_inputs_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.ifpkg"
            path.write_bytes(b"PK\x03\x04\xff")
            self.assertEqual("file.package", validate_path(path).errors[0].code)
            path = Path(tmp) / "invalid.yml"
            path.write_bytes(b"\xff")
            self.assertEqual("file.read", validate_path(path).errors[0].code)

    def test_cli_reports_selected_profile(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_dsl.py"),
                                 "--dify-version", "1.16.0", "--format", "json",
                                 str(ROOT / "examples/dify-1.18.0/02-agent-routes.yml")], capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertEqual("1.16", json.loads(result.stdout)["dify_version"])


if __name__ == "__main__":
    unittest.main()
