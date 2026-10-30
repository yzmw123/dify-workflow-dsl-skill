#!/usr/bin/env python3
"""Validate App DSL files with the node and Agent models from a Dify source tree.

This is a source-backed compatibility check. It exercises Dify's own Pydantic
models and lightweight graph validation without creating apps, writing a
database, installing plugins, or invoking models.
"""

from __future__ import annotations

import argparse
import inspect
import re
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
    parser.add_argument("--dify-version", help="Require this Dify major.minor or exact release, e.g. 1.18.0.")
    return parser


def _load_dify(source: Path) -> dict[str, Any]:
    api_path = source.resolve() / "api"
    if not (api_path / "pyproject.toml").is_file():
        raise RuntimeError(f"{source} is not a Dify source checkout with api/pyproject.toml")
    sys.path.insert(0, str(api_path))

    try:
        from constants.dsl_version import CURRENT_APP_DSL_VERSION
        from core.plugin.entities.plugin import PluginDependency
        from core.workflow.node_factory import resolve_workflow_node_class
        from models.agent_config_entities import WorkflowNodeJobConfig
        from services.agent.dsl_entities import AgentPackage
        from services.workflow_service import WorkflowService
    except Exception as exc:  # pragma: no cover - depends on the external Dify environment
        raise RuntimeError(
            "Could not import Dify. Use the source checkout's API environment with its locked dependencies "
            "(Dify 1.18: Python 3.13; Dify 1.16: Python 3.12)."
        ) from exc

    release_match = re.search(r'^version\s*=\s*"([^"]+)"', (api_path / "pyproject.toml").read_text(), re.M)
    extras = {}
    if release_match and release_match.group(1).startswith("1.18."):
        from services.entities.site_dsl import SiteDsl
        from services.agent.dsl_entities import AgentAppDsl
        extras = {"SiteDsl": SiteDsl, "AgentAppDsl": AgentAppDsl}
    return {
        **extras,
        "dify_version": release_match.group(1) if release_match else "unknown",
        "current_version": CURRENT_APP_DSL_VERSION,
        "PluginDependency": PluginDependency,
        "WorkflowNodeJobConfig": WorkflowNodeJobConfig,
        "AgentPackage": AgentPackage,
        "WorkflowService": WorkflowService,
        "resolve_node_class": resolve_workflow_node_class,
        "resolver_accepts_data": "node_data" in inspect.signature(resolve_workflow_node_class).parameters,
    }


def _validate_document(document: Any, dify: dict[str, Any], expected_version: str) -> list[str]:
    if not isinstance(document, dict):
        return ["top-level YAML must be a mapping"]

    errors: list[str] = []
    if "SiteDsl" in dify and document.get("site") is not None:
        try:
            dify["SiteDsl"].model_validate(document["site"])
        except Exception as exc:
            errors.append(f"site: {exc}")
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
    if not isinstance(mode, str):
        errors.append("app.mode must be a string")
        mode = None
    if mode == "agent":
        if "AgentAppDsl" in dify:
            try:
                dify["AgentAppDsl"].model_validate(document)
            except Exception as exc:
                errors.append(f"agent app: {exc}")
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
        if not isinstance(node_type, str):
            errors.append(f"node {node_id!r}: data.type must be a string")
            continue
        node_version = str(data.get("version") or "1")
        try:
            resolver_args = {"node_type": node_type, "node_version": node_version}
            if dify["resolver_accepts_data"]:
                resolver_args["node_data"] = data
            node_class = dify["resolve_node_class"](**resolver_args)
            node_class.validate_node_data(data)
        except Exception as exc:
            errors.append(f"node {node_id!r} ({node_type} v{node_version}): {exc}")

        if node_type == "agent" and node_version == "2" and data.get("agent_node_kind") == "dify_agent":
            try:
                job = dify["WorkflowNodeJobConfig"].model_validate(data.get("agent_job"))
                if hasattr(job, "output_routes"):
                    job.output_routes.validate_for_execution()
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
    if args.dify_version and not (dify["dify_version"] == args.dify_version or
                                 dify["dify_version"].startswith(args.dify_version + ".")):
        print(f"ERROR: Dify source is {dify['dify_version']}, expected {args.dify_version}", file=sys.stderr)
        return 2
    print(
        f"Dify source: {args.dify_source.resolve()} "
        f"(Dify {dify['dify_version']}; DSL {dify['current_version']})"
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
