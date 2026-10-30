"""Fast source-gate dispatch tests; official models are checked separately."""

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_with_dify_source import _validate_document


class GraphService:
    def validate_graph_structure(self, graph):
        pass


class SourceGateTests(unittest.TestCase):
    def setUp(self):
        self.node = Mock()
        self.resolve = Mock(return_value=self.node)
        self.job = Mock()
        self.dify = {"current_version": "0.7.0", "WorkflowService": GraphService,
                     "resolve_node_class": self.resolve, "resolver_accepts_data": True,
                     "WorkflowNodeJobConfig": self.job}

    def validate(self, *nodes):
        document = {"version": "0.7.0", "app": {"mode": "workflow"},
                    "workflow": {"graph": {"nodes": [{"id": str(i), "data": data}
                                                       for i, data in enumerate(nodes)], "edges": []}}}
        return _validate_document(document, self.dify, "0.7.0")

    def test_legacy_agent_version_two_uses_production_resolver(self):
        data = {"type": "agent", "version": "2", "agent_strategy_name": "function_calling"}
        self.assertEqual([], self.validate(data))
        self.resolve.assert_called_once_with(node_type="agent", node_version="2", node_data=data)
        self.node.validate_node_data.assert_called_once_with(data)
        self.job.model_validate.assert_not_called()

    def test_portable_agent_still_requires_package_and_job(self):
        self.job.model_validate.side_effect = ValueError("missing job")
        errors = self.validate({"type": "agent", "version": "2", "agent_node_kind": "dify_agent"})
        self.assertTrue(any("agent_job" in error for error in errors), errors)
        self.assertTrue(any("package_ref" in error for error in errors), errors)

    def test_legacy_resolver_signature_remains_supported(self):
        self.dify["resolver_accepts_data"] = False
        self.assertEqual([], self.validate({"type": "start"}))
        self.resolve.assert_called_once_with(node_type="start", node_version="1")

    def test_malformed_or_unknown_node_does_not_abort_other_nodes(self):
        for invalid in ([], {}, None):
            with self.subTest(invalid=invalid):
                self.assertIn("data.type must be a string", self.validate({"type": invalid}, {"type": "end"})[0])
        self.resolve.side_effect = [ValueError("unknown node type"), self.node]
        self.assertIn("unknown node type", self.validate({"type": "unknown"}, {"type": "end"})[0])

    def test_malformed_app_mode_returns_diagnostics(self):
        for app in (None, [], {}, {"mode": []}, {"mode": {}}):
            with self.subTest(app=app):
                errors = _validate_document({"version": "0.7.0", "app": app}, self.dify, "0.7.0")
                self.assertIn("app.mode must be a string", errors)


if __name__ == "__main__":
    unittest.main()
