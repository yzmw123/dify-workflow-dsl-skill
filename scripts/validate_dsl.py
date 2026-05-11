#!/usr/bin/env python3
"""Lightweight validator for Dify Workflow DSL YAML files."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


SUPPORTED_MODES = {"workflow", "advanced-chat", "chat", "completion", "agent-chat"}
TERMINAL_BY_MODE = {
    "workflow": "end",
    "advanced-chat": "answer",
}
GRAPH_MODES = {"workflow", "advanced-chat"}
DEPENDENCY_TYPES = {"marketplace", "package", "github"}
TRIGGER_TYPES = {"trigger-schedule", "trigger-webhook", "trigger-plugin"}

SQL_DANGEROUS_RE = re.compile(r"\b(drop|truncate|alter)\b", re.IGNORECASE)
SQL_MUTATING_RE = re.compile(r"\b(delete|update)\b", re.IGNORECASE)
SQL_TRAILING_COMMA_RE = re.compile(r"\([^;]*,\s*\)", re.IGNORECASE | re.DOTALL)
VAR_REF_RE = re.compile(r"\{\{#([^#{}]+)#\}\}")


class Report:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def walk(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
    else:
        yield value


def extract_tool_sql(data: dict[str, Any]) -> list[str]:
    sql_values: list[str] = []
    params = as_dict(data.get("tool_parameters"))
    for key in ("query", "sql"):
        param = as_dict(params.get(key))
        value = param.get("value")
        if isinstance(value, str):
            sql_values.append(value)
    return sql_values


def validate_file(path: Path) -> Report:
    report = Report(path)
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.error(f"YAML parse failed: {exc}")
        return report

    if not isinstance(document, dict):
        report.error("Top-level YAML must be a mapping.")
        return report

    version = document.get("version")
    if not isinstance(version, str):
        report.error("Top-level version must be a string, for example version: \"0.6.0\".")

    if document.get("kind") != "app":
        report.warn("Top-level kind is usually 'app'.")

    app = as_dict(document.get("app"))
    mode = app.get("mode")
    if mode not in SUPPORTED_MODES:
        report.error(f"app.mode is missing or unsupported: {mode!r}.")

    workflow = as_dict(document.get("workflow"))
    graph = as_dict(workflow.get("graph"))
    nodes = as_list(graph.get("nodes"))
    edges = as_list(graph.get("edges"))

    if mode in GRAPH_MODES:
        if not nodes:
            report.error("workflow.graph.nodes is missing or empty.")
        if "edges" not in graph:
            report.error("workflow.graph.edges is missing.")
    elif not nodes and "model_config" not in document:
        report.warn(f"Mode {mode!r} has no workflow graph and no model_config.")

    node_by_id: dict[str, dict[str, Any]] = {}
    node_type_by_id: dict[str, str] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            report.error(f"Node #{index} is not a mapping.")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str):
            report.error(f"Node #{index} id must be a string.")
            continue
        if node_id in node_by_id:
            report.error(f"Duplicate node id: {node_id}.")
        node_by_id[node_id] = node
        wrapper_type = node.get("type")
        data = as_dict(node.get("data"))
        if wrapper_type == "custom-note":
            continue
        node_type = data.get("type")
        if not isinstance(node_type, str):
            report.error(f"Node {node_id} missing data.type.")
            continue
        node_type_by_id[node_id] = node_type
        if wrapper_type not in {None, "custom", "custom-iteration-start", "custom-loop-start", "custom-note"}:
            report.warn(f"Node {node_id} wrapper type is unusual: {wrapper_type!r}.")

        validate_node(report, node_id, data)

    terminal = TERMINAL_BY_MODE.get(mode)
    if terminal and terminal not in node_type_by_id.values():
        has_trigger = any(node_type in TRIGGER_TYPES for node_type in node_type_by_id.values())
        if mode == "workflow" and has_trigger:
            report.warn(
                "Triggered workflow has no 'end' node. This can be valid for side-effect "
                "automations, but add an end node if callers need returned outputs."
            )
        else:
            report.warn(f"Mode {mode!r} usually needs a reachable {terminal!r} node.")

    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            report.error(f"Edge #{index} is not a mapping.")
            continue
        edge_id = edge.get("id")
        if isinstance(edge_id, str):
            if edge_id in edge_ids:
                report.error(f"Duplicate edge id: {edge_id}.")
            edge_ids.add(edge_id)

        source = edge.get("source")
        target = edge.get("target")
        if source not in node_by_id:
            report.error(f"Edge {edge_id or index} source does not exist: {source!r}.")
        if target not in node_by_id:
            report.error(f"Edge {edge_id or index} target does not exist: {target!r}.")

        data = as_dict(edge.get("data"))
        source_type = data.get("sourceType")
        target_type = data.get("targetType")
        if source in node_type_by_id and source_type and source_type != node_type_by_id[source]:
            report.error(
                f"Edge {edge_id or index} sourceType {source_type!r} does not match "
                f"node {source} type {node_type_by_id[source]!r}."
            )
        if target in node_type_by_id and target_type and target_type != node_type_by_id[target]:
            report.error(
                f"Edge {edge_id or index} targetType {target_type!r} does not match "
                f"node {target} type {node_type_by_id[target]!r}."
            )
        if edge.get("sourceHandle") is None:
            report.warn(f"Edge {edge_id or index} missing sourceHandle.")
        if edge.get("targetHandle") is None:
            report.warn(f"Edge {edge_id or index} missing targetHandle.")

    validate_variables(report, workflow)
    validate_dependencies(report, document)
    validate_references(report, document, set(node_by_id))
    return report


def validate_node(report: Report, node_id: str, data: dict[str, Any]) -> None:
    node_type = data.get("type")
    title = data.get("title", node_id)

    if node_type == "llm":
        model = as_dict(data.get("model"))
        if not model.get("provider") or not model.get("name"):
            report.warn(f"LLM node {node_id} ({title}) missing model.provider or model.name.")
        if not isinstance(data.get("prompt_template"), list):
            report.error(f"LLM node {node_id} ({title}) missing prompt_template list.")

    elif node_type == "code":
        code = data.get("code")
        code_language = str(data.get("code_language") or "python3").lower()
        if not isinstance(code, str):
            report.error(f"Code node {node_id} ({title}) missing code string.")
        elif code_language.startswith(("python", "py")) and "def main" not in code:
            report.error(f"Python code node {node_id} ({title}) must define def main(...).")
        elif code_language.startswith(("javascript", "typescript", "js", "ts")) and not re.search(
            r"\b(function\s+main|main\s*[:=]\s*(?:async\s*)?(?:function|\([^)]*\)\s*=>))",
            code,
        ):
            report.error(f"JavaScript code node {node_id} ({title}) must define main(...).")
        if not isinstance(data.get("outputs"), dict):
            report.error(f"Code node {node_id} ({title}) missing outputs mapping.")

    elif node_type == "tool":
        required = ["provider_id", "provider_name", "provider_type", "tool_name", "tool_parameters"]
        for key in required:
            if data.get(key) in (None, ""):
                report.error(f"Tool node {node_id} ({title}) missing {key}.")
        if data.get("plugin_id") and not data.get("plugin_unique_identifier"):
            report.warn(f"Tool node {node_id} ({title}) has plugin_id but no plugin_unique_identifier.")
        for sql in extract_tool_sql(data):
            if SQL_TRAILING_COMMA_RE.search(sql):
                report.error(f"Tool node {node_id} ({title}) SQL may contain a trailing comma before ')'.")
            if SQL_DANGEROUS_RE.search(sql):
                report.warn(f"Tool node {node_id} ({title}) SQL contains admin/destructive keyword.")
            if SQL_MUTATING_RE.search(sql):
                report.warn(f"Tool node {node_id} ({title}) SQL mutates data; confirm this is intentional.")

    elif node_type == "if-else":
        if not isinstance(data.get("cases"), list):
            report.error(f"If-else node {node_id} ({title}) missing cases list.")

    elif node_type == "start":
        variables = as_list(data.get("variables"))
        names = [v.get("variable") for v in variables if isinstance(v, dict)]
        duplicates = [name for name, count in Counter(names).items() if name and count > 1]
        if duplicates:
            report.error(f"Start node {node_id} ({title}) has duplicate variables: {duplicates}.")

    elif node_type == "answer":
        if "answer" not in data:
            report.error(f"Answer node {node_id} ({title}) missing answer.")

    elif node_type == "end":
        if not isinstance(data.get("outputs"), list):
            report.error(f"End node {node_id} ({title}) missing outputs list.")

    elif node_type == "parameter-extractor":
        if not isinstance(data.get("parameters"), list):
            report.error(f"Parameter extractor node {node_id} ({title}) missing parameters list.")


def validate_variables(report: Report, workflow: dict[str, Any]) -> None:
    for field in ("conversation_variables", "environment_variables"):
        variables = as_list(workflow.get(field))
        names = [v.get("name") for v in variables if isinstance(v, dict)]
        duplicates = [name for name, count in Counter(names).items() if name and count > 1]
        if duplicates:
            report.error(f"{field} has duplicate names: {duplicates}.")
        for variable in variables:
            if not isinstance(variable, dict):
                report.error(f"{field} contains a non-mapping item.")
                continue
            if not variable.get("name") or not variable.get("value_type"):
                report.warn(f"{field} item is missing name or value_type: {variable!r}.")


def validate_dependencies(report: Report, document: dict[str, Any]) -> None:
    dependencies = document.get("dependencies")
    if dependencies is None:
        return
    if not isinstance(dependencies, list):
        report.error("Top-level dependencies must be a list when present.")
        return

    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            report.error(f"Dependency #{index} is not a mapping.")
            continue
        dependency_type = dependency.get("type")
        value = as_dict(dependency.get("value"))
        if dependency_type not in DEPENDENCY_TYPES:
            report.error(f"Dependency #{index} has unsupported type: {dependency_type!r}.")
            continue
        if dependency_type == "marketplace":
            if not value.get("marketplace_plugin_unique_identifier"):
                report.error(f"Dependency #{index} marketplace value missing marketplace_plugin_unique_identifier.")
        elif dependency_type == "package":
            if not value.get("plugin_unique_identifier"):
                report.error(f"Dependency #{index} package value missing plugin_unique_identifier.")
        elif dependency_type == "github":
            required = ["repo", "version", "package", "github_plugin_unique_identifier"]
            missing = [key for key in required if not value.get(key)]
            if missing:
                report.error(f"Dependency #{index} github value missing: {missing}.")


def validate_references(report: Report, document: dict[str, Any], node_ids: set[str]) -> None:
    system_roots = {"sys", "conversation", "env", "context"}
    for value in walk(document):
        if not isinstance(value, str):
            continue
        for match in VAR_REF_RE.finditer(value):
            ref = match.group(1)
            root = ref.split(".", 1)[0]
            if root not in system_roots and root not in node_ids:
                report.warn(f"Variable reference points to unknown node/root: {match.group(0)}.")


def print_report(report: Report) -> None:
    print(f"== {report.path}")
    for error in report.errors:
        print(f"ERROR: {error}")
    for warning in report.warnings:
        print(f"WARN: {warning}")
    if not report.errors and not report.warnings:
        print("OK")
    else:
        print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Dify Workflow DSL YAML files.")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    exit_code = 0
    for path in args.files:
        report = validate_file(path)
        print_report(report)
        if report.errors:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
