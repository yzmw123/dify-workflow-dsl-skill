#!/usr/bin/env python3
"""Validate App DSL files with the node and Agent models from a Dify source tree.

This is a source-backed compatibility check. It exercises Dify's own Pydantic
models and lightweight graph validation without creating apps, writing a
database, installing plugins, or invoking models.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate DSL files with an installed Dify source environment.",
    )
    parser.add_argument(
        "--dify-source",
        type=Path,
        required=True,
        help="Path to a Dify source checkout, for example /path/to/dify-source.",
    )
    parser.add_argument(
        "--expected-version",
        default="0.7.0",
        help="Expected CURRENT_APP_DSL_VERSION from the Dify checkout (default: 0.7.0).",
    )
    parser.add_argument("files", nargs="+", type=Path, help="YAML files to validate.")
    return parser


def _load_dify(source: Path) -> dict[str, Any]:
    api_path = source.resolve() / "api"
    if not (api_path / "pyproject.toml").is_file():
        raise RuntimeError(f"{source} is not a Dify source checkout with api/pyproject.toml")
    sys.path.insert(0, str(api_path))

    try:
        from constants.dsl_version import CURRENT_APP_DSL_VERSION
        from core.plugin.entities.plugin import PluginDependency
        from core.workflow.node_factory import get_node_type_classes_mapping
        from models.agent_config_entities import WorkflowNodeJobConfig
        from services.agent.dsl_entities import AgentPackage
        from services.workflow_service import WorkflowService
    except Exception as exc:  # pragma: no cover - depends on the external Dify environment
        raise RuntimeError(
            "Could not import Dify. Run this script with Dify 1.16's Python 3.12 "
            "environment after installing its API dependencies."
        ) from exc

    return {
        "current_version": CURRENT_APP_DSL_VERSION,
        "PluginDependency": PluginDependency,
        "WorkflowNodeJobConfig": WorkflowNodeJobConfig,
        "AgentPackage": AgentPackage,
        "WorkflowService": WorkflowService,
        "registry": get_node_type_classes_mapping(),
    }


def _validate_document(document: Any, dify: dict[str, Any], expected_version: str) -> list[str]:
    if not isinstance(document, dict):
        return ["top-level YAML must be a mapping"]

    errors: list[str] = []
    current_version = dify["current_version"]
    if current_version != expected_version:
        errors.append(
            f"Dify checkout declares DSL {current_version!r}, expected {expected_version!r}"
        )
    if document.get("version") != current_version:
        errors.append(
            f"document version {document.get('version')!r} does not match Dify {current_version!r}"
        )

    dependencies = document.get("dependencies", [])
    if not isinstance(dependencies, list):
        errors.append("dependencies must be a list")
    else:
        for index, dependency in enumerate(dependencies):
            try:
                dify["PluginDependency"].model_validate(dependency)
            except Exception as exc:
                errors.append(f"dependencies[{index}]: {exc}")

    raw_packages = document.get("agent_packages", {})
    if not isinstance(raw_packages, dict):
        errors.append("agent_packages must be a mapping")
        raw_packages = {}
    else:
        for package_ref, package in raw_packages.items():
            try:
                dify["AgentPackage"].model_validate(package)
            except Exception as exc:
                errors.append(f"agent_packages.{package_ref}: {exc}")

    app = document.get("app")
    mode = app.get("mode") if isinstance(app, dict) else None
    if mode == "agent":
        agent = document.get("agent")
        package_ref = agent.get("package_ref") if isinstance(agent, dict) else None
        if not isinstance(package_ref, str) or package_ref not in raw_packages:
            errors.append("agent.package_ref does not resolve to agent_packages")

    workflow = document.get("workflow")
    if not isinstance(workflow, dict):
        if mode in {"workflow", "advanced-chat"}:
            errors.append(f"{mode} app is missing workflow")
        return errors

    graph = workflow.get("graph")
    if not isinstance(graph, dict):
        errors.append("workflow.graph must be a mapping")
        return errors

    service = dify["WorkflowService"].__new__(dify["WorkflowService"])
    try:
        service.validate_graph_structure(graph)
    except Exception as exc:
        errors.append(f"workflow.graph: {exc}")

    nodes = graph.get("nodes", [])
    if not isinstance(nodes, list):
        errors.append("workflow.graph.nodes must be a list")
        return errors

    registry = dify["registry"]
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"workflow.graph.nodes[{index}] must be a mapping")
            continue
        if node.get("type") == "custom-note":
            continue
        data = node.get("data")
        if not isinstance(data, dict):
            errors.append(f"workflow.graph.nodes[{index}].data must be a mapping")
            continue
        node_id = node.get("id", index)
        node_type = data.get("type")
        versions = registry.get(node_type)
        if not versions:
            errors.append(f"node {node_id!r}: Dify has no registered node type {node_type!r}")
            continue
        node_version = str(data.get("version") or "1")
        node_class = versions.get(node_version) or versions.get("latest")
        try:
            node_class.validate_node_data(data)
        except Exception as exc:
            errors.append(f"node {node_id!r} ({node_type} v{node_version}): {exc}")

        if node_type == "agent" and node_version == "2":
            try:
                dify["WorkflowNodeJobConfig"].model_validate(data.get("agent_job"))
            except Exception as exc:
                errors.append(f"node {node_id!r}.agent_job: {exc}")
            binding = data.get("agent_binding")
            package_ref = binding.get("package_ref") if isinstance(binding, dict) else None
            if not isinstance(package_ref, str) or package_ref not in raw_packages:
                errors.append(f"node {node_id!r}.agent_binding.package_ref is unresolved")

    return errors


def main() -> int:
    args = _parser().parse_args()
    try:
        dify = _load_dify(args.dify_source)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if exc.__cause__ is not None:
            print(f"CAUSE: {exc.__cause__}", file=sys.stderr)
        return 2

    failed = False
    print(
        f"Dify source: {args.dify_source.resolve()} "
        f"(DSL {dify['current_version']})"
    )
    for path in args.files:
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors = [f"could not parse YAML: {exc}"]
        else:
            errors = _validate_document(document, dify, args.expected_version)
        if errors:
            failed = True
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
