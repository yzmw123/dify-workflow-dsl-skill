"""Version-aware structural validator for portable Dify App DSL files."""

from __future__ import annotations

import re
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

from .models import Report


SUPPORTED_VERSIONS = ("0.6.0", "0.7.0")
GRAPH_MODES = {"workflow", "advanced-chat"}
BASE_MODES = {"workflow", "advanced-chat", "chat", "completion", "agent-chat"}
MODES_BY_VERSION = {
    "0.6.0": BASE_MODES,
    "0.7.0": BASE_MODES | {"agent"},
}
DEPENDENCY_TYPES = {"marketplace", "package", "github"}
TRIGGER_TYPES = {"trigger-schedule", "trigger-webhook", "trigger-plugin"}
ENTRY_TYPES = {"start"} | TRIGGER_TYPES
TERMINAL_TYPES = {
    "workflow": {"end"},
    "advanced-chat": {"answer"},
}
SYSTEM_ROOTS = {"sys", "conversation", "env", "context", "$output"}
WRAPPER_TYPES = {"custom", "custom-iteration-start", "custom-loop-start", "custom-note"}

VAR_REF_RE = re.compile(r"\{\{#([^#{}]+)#\}\}")
HUMAN_OUTPUT_RE = re.compile(r"\{\{#\$output\.([A-Za-z_][A-Za-z0-9_]{0,29})#\}\}")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
NODE_ID_RE = re.compile(r"^[A-Za-z0-9_:-]+$")
SQL_DESTRUCTIVE_RE = re.compile(r"\b(drop|truncate|alter)\b", re.IGNORECASE)
SQL_MUTATING_RE = re.compile(r"\b(delete|update|insert|merge|replace)\b", re.IGNORECASE)
SQL_TRAILING_COMMA_RE = re.compile(r"\([^;]*,\s*\)", re.IGNORECASE | re.DOTALL)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _duplicates(values: Iterable[Any]) -> list[Any]:
    return sorted(
        (value for value, count in Counter(values).items() if value and count > 1),
        key=repr,
    )


def _handle_id(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _walk(value: Any, path: str = "") -> Iterator[tuple[str, str, Any]]:
    """Yield ``(path, key, value)`` for every nested mapping value."""

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield child_path, str(key), child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from _walk(child, child_path)


def _plugin_id(value: Any) -> str | None:
    """Normalize a provider or dependency identifier to ``author/plugin``."""

    if not isinstance(value, str):
        return None
    candidate = value.strip().split("@", 1)[0].split(":", 1)[0]
    parts = [part for part in candidate.split("/") if part]
    if len(parts) < 2:
        return None
    return "/".join(parts[:2])


def _declared_output_name(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    value = item.get("name", item.get("variable"))
    return value if isinstance(value, str) and value else None


class Validator:
    def __init__(self, document: Any, path: Path, target_version: str | None = None) -> None:
        self.document = document
        self.report = Report(path)
        self.target_version = target_version
        self.version: str | None = None
        self.mode: str | None = None
        self.workflow: dict[str, Any] = {}
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.node_by_id: dict[str, dict[str, Any]] = {}
        self.node_type_by_id: dict[str, str] = {}
        self.output_names_by_node: dict[str, set[str] | None] = {}
        self.agent_packages: dict[str, Any] = {}

    def run(self) -> Report:
        if not isinstance(self.document, dict):
            self.report.error("document.type", "Top-level YAML must be a mapping.", "$")
            return self.report

        self._validate_header()
        self._validate_agent_packages()
        self._load_graph()
        if self.mode in GRAPH_MODES:
            self._validate_nodes()
            self._validate_edges()
            self._validate_graph_shape()
            self._validate_variables()
            self._validate_references()
        elif self.mode == "agent":
            self._validate_agent_app()
        elif not self.document.get("model_config"):
            self.report.warn(
                "app.config-missing",
                f"Mode {self.mode!r} has neither a workflow graph nor model_config.",
                "model_config",
            )
        self._validate_dependencies()
        return self.report

    def _validate_header(self) -> None:
        raw_version = self.document.get("version")
        if not isinstance(raw_version, str):
            self.report.error(
                "version.type",
                'Top-level version must be a quoted string such as "0.7.0".',
                "version",
            )
        else:
            self.version = raw_version
            if raw_version not in SUPPORTED_VERSIONS:
                self.report.error(
                    "version.unsupported",
                    f"Unsupported DSL version {raw_version!r}; supported versions: {', '.join(SUPPORTED_VERSIONS)}.",
                    "version",
                )

        if self.target_version is not None and raw_version != self.target_version:
            self.report.error(
                "version.target-mismatch",
                f"Document version {raw_version!r} does not match requested target {self.target_version!r}.",
                "version",
            )

        if self.document.get("kind") != "app":
            self.report.warn("document.kind", "Top-level kind should be 'app'.", "kind")

        app = self.document.get("app")
        if not isinstance(app, dict):
            self.report.error("app.type", "Top-level app must be a mapping.", "app")
            app = {}
        if not isinstance(app.get("name"), str) or not app.get("name"):
            self.report.warn("app.name", "app.name is missing or empty.", "app.name")
        mode = app.get("mode")
        if not isinstance(mode, str):
            self.report.error("app.mode", "app.mode must be a string.", "app.mode")
            return
        self.mode = mode
        allowed_modes = MODES_BY_VERSION.get(self.version, BASE_MODES | {"agent"})
        if mode not in allowed_modes:
            if mode == "agent" and self.version == "0.6.0":
                message = "Agent App mode requires DSL 0.7.0."
            else:
                message = f"Unsupported app.mode {mode!r} for DSL {self.version!r}."
            self.report.error("app.mode", message, "app.mode")

    def _validate_agent_packages(self) -> None:
        raw_packages = self.document.get("agent_packages")
        if raw_packages is None:
            self.agent_packages = {}
            return
        if self.version == "0.6.0":
            self.report.error(
                "version.feature-agent-packages",
                "agent_packages is a DSL 0.7.0 feature.",
                "agent_packages",
            )
        if not isinstance(raw_packages, dict):
            self.report.error("agent.packages-type", "agent_packages must be a mapping.", "agent_packages")
            return
        self.agent_packages = raw_packages
        for ref, raw_package in raw_packages.items():
            location = f"agent_packages.{ref}"
            if not isinstance(ref, str) or not ref:
                self.report.error("agent.package-key", "Package keys must be non-empty strings.", location)
                continue
            if not isinstance(raw_package, dict):
                self.report.error("agent.package-type", "Agent package must be a mapping.", location)
                continue
            if raw_package.get("schema_version", 1) != 1:
                self.report.error(
                    "agent.package-schema",
                    "Agent package schema_version must be 1.",
                    f"{location}.schema_version",
                )
            metadata = raw_package.get("metadata")
            if (
                not isinstance(metadata, dict)
                or not isinstance(metadata.get("name"), str)
                or not metadata.get("name")
            ):
                self.report.error(
                    "agent.package-metadata",
                    "Agent package metadata.name must be a non-empty string.",
                    f"{location}.metadata.name",
                )
            soul = raw_package.get("soul")
            if not isinstance(soul, dict):
                self.report.error("agent.package-soul", "Agent package soul must be a mapping.", f"{location}.soul")
            elif soul.get("schema_version", 1) != 1:
                self.report.error(
                    "agent.soul-schema",
                    "Agent soul schema_version must be 1.",
                    f"{location}.soul.schema_version",
                )
            omitted_assets = raw_package.get("omitted_assets", [])
            if not isinstance(omitted_assets, list):
                self.report.error(
                    "agent.omitted-assets",
                    "omitted_assets must be a list.",
                    f"{location}.omitted_assets",
                )
            else:
                for index, asset in enumerate(omitted_assets):
                    asset_path = f"{location}.omitted_assets[{index}]"
                    valid_asset = (
                        isinstance(asset, dict)
                        and asset.get("kind") in {"skill", "file"}
                        and bool(asset.get("name"))
                    )
                    if not valid_asset:
                        self.report.error(
                            "agent.omitted-asset",
                            "Each omitted asset needs kind ('skill' or 'file') and name.",
                            asset_path,
                        )

    def _validate_agent_app(self) -> None:
        raw_agent = self.document.get("agent")
        if not isinstance(raw_agent, dict):
            self.report.error("agent.app-config", "Agent App requires a top-level agent mapping.", "agent")
            return
        self._validate_package_ref(raw_agent.get("package_ref"), "agent.package_ref")

    def _validate_package_ref(self, package_ref: Any, location: str) -> None:
        if not isinstance(package_ref, str) or not package_ref or package_ref not in self.agent_packages:
            self.report.error(
                "agent.package-ref",
                f"Agent package_ref {package_ref!r} does not resolve to agent_packages.",
                location,
            )

    def _load_graph(self) -> None:
        if self.mode not in GRAPH_MODES:
            return
        raw_workflow = self.document.get("workflow")
        if not isinstance(raw_workflow, dict):
            self.report.error("workflow.type", "Graph modes require a workflow mapping.", "workflow")
            return
        self.workflow = raw_workflow
        graph = raw_workflow.get("graph")
        if not isinstance(graph, dict):
            self.report.error("graph.type", "workflow.graph must be a mapping.", "workflow.graph")
            return
        raw_nodes = graph.get("nodes")
        raw_edges = graph.get("edges")
        if not isinstance(raw_nodes, list):
            self.report.error("graph.nodes-type", "workflow.graph.nodes must be a list.", "workflow.graph.nodes")
        else:
            self.nodes = [item for item in raw_nodes if isinstance(item, dict)]
            for index, item in enumerate(raw_nodes):
                if not isinstance(item, dict):
                    self.report.error("node.type", "Node must be a mapping.", f"workflow.graph.nodes[{index}]")
        if not isinstance(raw_edges, list):
            self.report.error("graph.edges-type", "workflow.graph.edges must be a list.", "workflow.graph.edges")
        else:
            self.edges = [item for item in raw_edges if isinstance(item, dict)]
            for index, item in enumerate(raw_edges):
                if not isinstance(item, dict):
                    self.report.error("edge.type", "Edge must be a mapping.", f"workflow.graph.edges[{index}]")

    def _validate_nodes(self) -> None:
        if not self.nodes:
            self.report.error("graph.nodes-empty", "workflow.graph.nodes is empty.", "workflow.graph.nodes")
            return
        for index, node in enumerate(self.nodes):
            location = f"workflow.graph.nodes[{index}]"
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                self.report.error("node.id", "Node id must be a non-empty string.", f"{location}.id")
                continue
            if not NODE_ID_RE.fullmatch(node_id):
                self.report.error(
                    "node.invalid-id",
                    "Node id must contain only letters, numbers, underscores, colons, or hyphens.",
                    f"{location}.id",
                )
            if node_id in self.node_by_id:
                self.report.error("node.duplicate-id", f"Duplicate node id {node_id!r}.", f"{location}.id")
                continue
            self.node_by_id[node_id] = node

            wrapper_type = node.get("type")
            if wrapper_type not in WRAPPER_TYPES:
                self.report.warn(
                    "node.wrapper-type",
                    f"Node wrapper type {wrapper_type!r} is unusual.",
                    f"{location}.type",
                )
            if wrapper_type == "custom-note":
                continue

            data = node.get("data")
            if not isinstance(data, dict):
                self.report.error("node.data", "Runtime node data must be a mapping.", f"{location}.data")
                continue
            node_type = data.get("type")
            if not isinstance(node_type, str) or not node_type:
                self.report.error("node.data-type", "Runtime node is missing data.type.", f"{location}.data.type")
                continue
            self.node_type_by_id[node_id] = node_type
            self.output_names_by_node[node_id] = self._validate_node(node_id, data, f"{location}.data")

    def _validate_node(self, node_id: str, data: dict[str, Any], location: str) -> set[str] | None:
        node_type = data.get("type")
        title = data.get("title", node_id)
        outputs: set[str] | None = set()

        if node_type == "start":
            variables = data.get("variables")
            if not isinstance(variables, list):
                self.report.error(
                    "node.start.variables",
                    "Start node variables must be a list.",
                    f"{location}.variables",
                )
                return outputs
            names = [item.get("variable") for item in variables if isinstance(item, dict)]
            duplicates = _duplicates(names)
            if duplicates:
                self.report.error(
                    "node.start.duplicate-variable",
                    f"Start node has duplicate variables: {duplicates}.",
                    f"{location}.variables",
                )
            for index, item in enumerate(variables):
                item_path = f"{location}.variables[{index}]"
                if not isinstance(item, dict) or not isinstance(item.get("variable"), str) or not item.get("variable"):
                    self.report.error("node.start.variable", "Start variable needs a variable name.", item_path)
                    continue
                outputs.add(item["variable"])

        elif node_type == "llm":
            model = data.get("model")
            if not isinstance(model, dict) or not model.get("provider") or not model.get("name"):
                self.report.warn(
                    "node.llm.model",
                    f"LLM node {title!r} has no explicit model provider/name and will depend on workspace defaults.",
                    f"{location}.model",
                )
            if not isinstance(data.get("prompt_template"), list):
                self.report.error(
                    "node.llm.prompt",
                    "LLM prompt_template must be a list.",
                    f"{location}.prompt_template",
                )
            outputs = {"text", "reasoning_content", "usage", "finish_reason", "structured_output"}

        elif node_type == "code":
            code = data.get("code")
            language = str(data.get("code_language") or "python3").lower()
            if not isinstance(code, str):
                self.report.error("node.code.source", "Code node must contain a code string.", f"{location}.code")
            elif language.startswith(("python", "py")) and not re.search(r"\bdef\s+main\s*\(", code):
                self.report.error("node.code.entrypoint", "Python code must define def main(...).", f"{location}.code")
            elif language.startswith(("javascript", "typescript", "js", "ts")) and not re.search(
                r"\b(function\s+main|main\s*[:=]\s*(?:async\s*)?(?:function|\([^)]*\)\s*=>))",
                code,
            ):
                self.report.error("node.code.entrypoint", "JavaScript code must define main(...).", f"{location}.code")
            raw_outputs = data.get("outputs")
            if not isinstance(raw_outputs, dict):
                self.report.error("node.code.outputs", "Code node outputs must be a mapping.", f"{location}.outputs")
            else:
                outputs = {str(name) for name in raw_outputs}

        elif node_type == "tool":
            for key in ("provider_id", "provider_name", "provider_type", "tool_name", "tool_parameters"):
                if data.get(key) in (None, ""):
                    self.report.error("node.tool.field", f"Tool node is missing {key}.", f"{location}.{key}")
            self._validate_tool_sql(data, location)
            outputs = None  # Tool schemas are installed dynamically.

        elif node_type == "if-else":
            cases = data.get("cases")
            if not isinstance(cases, list) or not cases:
                self.report.error(
                    "node.if-else.cases",
                    "If-else node needs a non-empty cases list.",
                    f"{location}.cases",
                )

        elif node_type == "question-classifier":
            classes = data.get("classes")
            if not isinstance(classes, list) or not classes:
                self.report.error(
                    "node.question-classifier.classes",
                    "Question classifier needs a non-empty classes list.",
                    f"{location}.classes",
                )
            outputs = {"class_name"}

        elif node_type == "answer":
            if "answer" not in data:
                self.report.error("node.answer.value", "Answer node is missing answer.", f"{location}.answer")

        elif node_type == "end":
            raw_outputs = data.get("outputs")
            if not isinstance(raw_outputs, list):
                self.report.error("node.end.outputs", "End node outputs must be a list.", f"{location}.outputs")

        elif node_type == "parameter-extractor":
            parameters = data.get("parameters")
            if not isinstance(parameters, list):
                self.report.error(
                    "node.parameter-extractor.parameters",
                    "Parameter extractor parameters must be a list.",
                    f"{location}.parameters",
                )
            else:
                outputs = {name for item in parameters if (name := _declared_output_name(item))}

        elif node_type == "human-input":
            outputs = self._validate_human_input(data, location)

        elif node_type == "agent":
            outputs = self._validate_agent_node(data, location)

        elif node_type == "template-transform":
            outputs = {"output"}
        elif node_type == "http-request":
            outputs = {"body", "status_code", "headers", "files"}
        elif node_type == "knowledge-retrieval":
            outputs = {"result"}
        elif node_type == "document-extractor":
            outputs = {"text"}
        elif node_type == "list-operator":
            outputs = {"result", "first_record", "last_record"}
        elif node_type == "variable-aggregator":
            outputs = {"output"}
        elif node_type in {"iteration", "loop"}:
            outputs = {"output"}
        elif node_type in TRIGGER_TYPES:
            outputs = None
        elif node_type in {"assigner", "iteration-start", "loop-start"}:
            outputs = set()
        else:
            self.report.warn(
                "node.unknown-type",
                f"Node type {node_type!r} is not covered by a strict schema; dynamic outputs will be accepted.",
                f"{location}.type",
            )
            outputs = None
        return outputs

    def _validate_human_input(self, data: dict[str, Any], location: str) -> set[str]:
        for key in ("delivery_methods", "inputs", "user_actions"):
            if not isinstance(data.get(key), list):
                self.report.error(
                    f"node.human-input.{key.replace('_', '-')}",
                    f"Human Input {key} must be a list.",
                    f"{location}.{key}",
                )
        if not isinstance(data.get("form_content"), str):
            self.report.error(
                "node.human-input.form-content",
                "Human Input form_content must be a string.",
                f"{location}.form_content",
            )
        timeout = data.get("timeout")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            self.report.error(
                "node.human-input.timeout",
                "Human Input timeout must be a positive integer.",
                f"{location}.timeout",
            )
        if data.get("timeout_unit") not in {"hour", "day"}:
            self.report.error(
                "node.human-input.timeout-unit",
                "Human Input timeout_unit must be 'hour' or 'day'.",
                f"{location}.timeout_unit",
            )

        outputs: set[str] = {"__action_id", "__action_value", "__rendered_content"}
        form_content = data.get("form_content")
        if isinstance(form_content, str):
            outputs.update(HUMAN_OUTPUT_RE.findall(form_content))
        inputs = _list(data.get("inputs"))
        input_names = [item.get("output_variable_name") for item in inputs if isinstance(item, dict)]
        duplicates = _duplicates(input_names)
        if duplicates:
            self.report.error(
                "node.human-input.duplicate-input",
                f"Human Input has duplicate output_variable_name values: {duplicates}.",
                f"{location}.inputs",
            )
        for index, item in enumerate(inputs):
            item_path = f"{location}.inputs[{index}]"
            if not isinstance(item, dict):
                self.report.error("node.human-input.input", "Human Input item must be a mapping.", item_path)
                continue
            name = item.get("output_variable_name")
            if not isinstance(name, str) or not IDENTIFIER_RE.fullmatch(name):
                self.report.error(
                    "node.human-input.input-name",
                    "output_variable_name must be a valid identifier.",
                    f"{item_path}.output_variable_name",
                )
            else:
                outputs.add(name)
            if item.get("type") not in {"paragraph", "select", "file", "file-list"}:
                self.report.error(
                    "node.human-input.input-type",
                    "Input type must be paragraph, select, file, or file-list.",
                    f"{item_path}.type",
                )

        actions = _list(data.get("user_actions"))
        action_ids = [item.get("id") for item in actions if isinstance(item, dict)]
        duplicates = _duplicates(action_ids)
        if duplicates:
            self.report.error(
                "node.human-input.duplicate-action",
                f"Human Input has duplicate user action ids: {duplicates}.",
                f"{location}.user_actions",
            )
        for index, action in enumerate(actions):
            action_path = f"{location}.user_actions[{index}]"
            if not isinstance(action, dict):
                self.report.error("node.human-input.action", "User action must be a mapping.", action_path)
                continue
            action_id = action.get("id")
            if not isinstance(action_id, str) or len(action_id) > 20 or not IDENTIFIER_RE.fullmatch(action_id):
                self.report.error(
                    "node.human-input.action-id",
                    "Action id must be an identifier of at most 20 characters.",
                    f"{action_path}.id",
                )
            if not isinstance(action.get("title"), str) or not action.get("title") or len(action["title"]) > 100:
                self.report.error(
                    "node.human-input.action-title",
                    "Action title must contain 1-100 characters.",
                    f"{action_path}.title",
                )
            if action.get("button_style", "default") not in {"primary", "default", "accent", "ghost"}:
                self.report.error(
                    "node.human-input.button-style",
                    "button_style must be primary, default, accent, or ghost.",
                    f"{action_path}.button_style",
                )
        return outputs

    def _validate_agent_node(self, data: dict[str, Any], location: str) -> set[str] | None:
        is_v2 = (
            any(key in data for key in ("agent_node_kind", "agent_binding", "agent_job"))
            or data.get("version") == "2"
        )
        if not is_v2:
            for key in ("agent_strategy_provider_name", "agent_strategy_name", "agent_parameters"):
                if data.get(key) in (None, ""):
                    self.report.error(
                        "node.agent-legacy.field",
                        f"Legacy Agent node is missing {key}.",
                        f"{location}.{key}",
                    )
            # Strategy plugins determine their own output schema.
            return None
        if self.version != "0.7.0":
            self.report.error("version.feature-agent-v2", "Agent v2 workflow nodes require DSL 0.7.0.", location)
        if data.get("version") != "2" or data.get("agent_node_kind") != "dify_agent":
            self.report.error(
                "node.agent-v2.identity",
                "Portable Agent node requires version: '2' and agent_node_kind: dify_agent.",
                location,
            )
        binding = data.get("agent_binding")
        if not isinstance(binding, dict):
            self.report.error(
                "node.agent-v2.binding",
                "Agent v2 needs an agent_binding mapping.",
                f"{location}.agent_binding",
            )
        else:
            if binding.get("binding_type") not in {"inline_agent", "roster_agent"}:
                self.report.error(
                    "node.agent-v2.binding-type",
                    "agent_binding.binding_type must be inline_agent or roster_agent.",
                    f"{location}.agent_binding.binding_type",
                )
            self._validate_package_ref(binding.get("package_ref"), f"{location}.agent_binding.package_ref")
        job = data.get("agent_job")
        if not isinstance(job, dict):
            self.report.error("node.agent-v2.job", "Agent v2 needs an agent_job mapping.", f"{location}.agent_job")
            return {"text", "files", "json"}
        if job.get("schema_version", 1) != 1:
            self.report.error(
                "node.agent-v2.job-schema",
                "agent_job.schema_version must be 1.",
                f"{location}.agent_job.schema_version",
            )
        for key in ("previous_node_output_refs", "declared_outputs", "human_contacts"):
            if key in job and not isinstance(job[key], list):
                self.report.error(
                    "node.agent-v2.job-field",
                    f"agent_job.{key} must be a list.",
                    f"{location}.agent_job.{key}",
                )
        declared = _list(job.get("declared_outputs"))
        names = {name for item in declared if (name := _declared_output_name(item))}
        return names or {"text", "files", "json"}

    def _validate_tool_sql(self, data: dict[str, Any], location: str) -> None:
        parameters = _dict(data.get("tool_parameters"))
        for key in ("query", "sql"):
            parameter = parameters.get(key)
            value = parameter.get("value") if isinstance(parameter, dict) else parameter
            if not isinstance(value, str):
                continue
            sql_path = f"{location}.tool_parameters.{key}"
            if SQL_TRAILING_COMMA_RE.search(value):
                self.report.error(
                    "sql.trailing-comma",
                    "SQL appears to contain a trailing comma before ')'.",
                    sql_path,
                )
            if SQL_DESTRUCTIVE_RE.search(value):
                self.report.warn("sql.destructive", "SQL contains an administrative or destructive keyword.", sql_path)
            if SQL_MUTATING_RE.search(value):
                self.report.warn("sql.mutating", "SQL mutates data; confirm this is intentional.", sql_path)
            if VAR_REF_RE.search(value):
                self.report.warn(
                    "sql.interpolation",
                    "SQL contains direct Dify template interpolation; use bound "
                    "parameters when the tool supports them.",
                    sql_path,
                )
            statements = [statement for statement in value.split(";") if statement.strip()]
            if len(statements) > 1:
                self.report.warn("sql.multiple-statements", "SQL contains multiple statements.", sql_path)

    def _validate_edges(self) -> None:
        edge_ids: set[str] = set()
        endpoint_pairs: set[tuple[Any, Any, Any]] = set()
        for index, edge in enumerate(self.edges):
            location = f"workflow.graph.edges[{index}]"
            edge_id = edge.get("id")
            if not isinstance(edge_id, str) or not edge_id:
                self.report.error("edge.id", "Edge id must be a non-empty string.", f"{location}.id")
            elif edge_id in edge_ids:
                self.report.error("edge.duplicate-id", f"Duplicate edge id {edge_id!r}.", f"{location}.id")
            else:
                edge_ids.add(edge_id)

            source = edge.get("source")
            target = edge.get("target")
            if source not in self.node_type_by_id:
                self.report.error("edge.source", f"Edge source {source!r} is not a runtime node.", f"{location}.source")
            if target not in self.node_type_by_id:
                self.report.error("edge.target", f"Edge target {target!r} is not a runtime node.", f"{location}.target")
            pair = (source, edge.get("sourceHandle"), target)
            if pair in endpoint_pairs:
                self.report.warn("edge.duplicate", "Duplicate source/handle/target edge.", location)
            endpoint_pairs.add(pair)

            data = _dict(edge.get("data"))
            source_type = data.get("sourceType")
            target_type = data.get("targetType")
            if source in self.node_type_by_id and source_type and source_type != self.node_type_by_id[source]:
                self.report.error(
                    "edge.source-type",
                    f"sourceType {source_type!r} does not match {self.node_type_by_id[source]!r}.",
                    f"{location}.data.sourceType",
                )
            if target in self.node_type_by_id and target_type and target_type != self.node_type_by_id[target]:
                self.report.error(
                    "edge.target-type",
                    f"targetType {target_type!r} does not match {self.node_type_by_id[target]!r}.",
                    f"{location}.data.targetType",
                )
            if edge.get("sourceHandle") is None:
                self.report.warn("edge.source-handle", "Edge is missing sourceHandle.", f"{location}.sourceHandle")
            if edge.get("targetHandle") is None:
                self.report.warn("edge.target-handle", "Edge is missing targetHandle.", f"{location}.targetHandle")
            self._validate_branch_handle(edge, location)

    def _validate_branch_handle(self, edge: dict[str, Any], location: str) -> None:
        source = edge.get("source")
        if source not in self.node_by_id:
            return
        node_type = self.node_type_by_id.get(source)
        data = _dict(self.node_by_id[source].get("data"))
        allowed: set[str] | None = None
        if node_type == "if-else":
            allowed = {"false"}
            for case in _list(data.get("cases")):
                if isinstance(case, dict):
                    value = case.get("case_id", case.get("id"))
                    if value is not None:
                        allowed.add(_handle_id(value))
        elif node_type == "question-classifier":
            allowed = set()
            for item in _list(data.get("classes")):
                if isinstance(item, dict) and item.get("id") is not None:
                    allowed.add(_handle_id(item["id"]))
        elif node_type == "human-input":
            allowed = {
                _handle_id(item["id"])
                for item in _list(data.get("user_actions"))
                if isinstance(item, dict) and item.get("id") is not None
            }
            # The 1.16 frontend/export uses __timeout while the backend HITL
            # adapter currently names the selected runtime handle __timeout__.
            allowed.update({"__timeout", "__timeout__"})
        if allowed is not None and _handle_id(edge.get("sourceHandle")) not in allowed:
            self.report.error(
                "edge.invalid-branch-handle",
                f"sourceHandle {edge.get('sourceHandle')!r} is not one of {sorted(allowed)}.",
                f"{location}.sourceHandle",
            )

    def _validate_graph_shape(self) -> None:
        runtime_ids = set(self.node_type_by_id)
        entries = [node_id for node_id, node_type in self.node_type_by_id.items() if node_type in ENTRY_TYPES]
        if not entries:
            self.report.error("graph.entry", "Graph needs a start or trigger entry node.", "workflow.graph.nodes")
        elif self.mode == "advanced-chat" and [self.node_type_by_id[node_id] for node_id in entries] != ["start"]:
            self.report.error("graph.entry", "Advanced chat requires exactly one start node.", "workflow.graph.nodes")
        elif len(entries) > 1:
            self.report.warn(
                "graph.multiple-entry",
                f"Graph has multiple entry nodes: {entries}.",
                "workflow.graph.nodes",
            )

        expected_terminal_types = TERMINAL_TYPES.get(self.mode or "", set())
        terminals = [
            node_id for node_id, node_type in self.node_type_by_id.items() if node_type in expected_terminal_types
        ]
        has_trigger = any(node_type in TRIGGER_TYPES for node_type in self.node_type_by_id.values())
        if not terminals:
            if self.mode == "workflow" and has_trigger:
                self.report.warn(
                    "graph.terminal-missing",
                    "Triggered workflow has no end node; valid for side effects but it returns no outputs.",
                    "workflow.graph.nodes",
                )
            else:
                required = ", ".join(sorted(expected_terminal_types)) or "terminal"
                self.report.error("graph.terminal-missing", f"Graph needs a {required} node.", "workflow.graph.nodes")

        adjacency: dict[str, set[str]] = {node_id: set() for node_id in runtime_ids}
        indegree: dict[str, int] = {node_id: 0 for node_id in runtime_ids}
        for edge in self.edges:
            source, target = edge.get("source"), edge.get("target")
            if source in runtime_ids and target in runtime_ids and target not in adjacency[source]:
                adjacency[source].add(target)
                indegree[target] += 1

        # Container internals are reached through their configured start helper.
        for node_id, node in self.node_by_id.items():
            data = _dict(node.get("data"))
            start_id = data.get("start_node_id")
            if node_id in runtime_ids and start_id in runtime_ids and start_id not in adjacency[node_id]:
                adjacency[node_id].add(start_id)
                indegree[start_id] += 1

        reachable: set[str] = set()
        queue = deque(entry for entry in entries if entry in runtime_ids)
        while queue:
            node_id = queue.popleft()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            queue.extend(adjacency[node_id] - reachable)

        for node_id in sorted(runtime_ids - reachable):
            self.report.error(
                "graph.unreachable-node",
                f"Node {node_id!r} is not reachable from any graph entry.",
                f"workflow.graph.nodes[{node_id}]",
            )
        for node_id in terminals:
            if node_id not in reachable:
                self.report.error(
                    "graph.unreachable-terminal",
                    f"Terminal node {node_id!r} is unreachable.",
                    f"workflow.graph.nodes[{node_id}]",
                )

        processed = 0
        kahn = deque(node_id for node_id, degree in indegree.items() if degree == 0)
        while kahn:
            node_id = kahn.popleft()
            processed += 1
            for target in adjacency[node_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    kahn.append(target)
        if processed != len(runtime_ids):
            cyclic = sorted(node_id for node_id, degree in indegree.items() if degree > 0)
            self.report.error(
                "graph.cycle",
                f"Graph contains a cycle involving: {cyclic}.",
                "workflow.graph.edges",
            )

    def _validate_variables(self) -> None:
        for field in ("conversation_variables", "environment_variables"):
            raw_variables = self.workflow.get(field, [])
            location = f"workflow.{field}"
            if not isinstance(raw_variables, list):
                self.report.error("workflow.variables-type", f"{field} must be a list.", location)
                continue
            names = [item.get("name") for item in raw_variables if isinstance(item, dict)]
            duplicates = _duplicates(names)
            if duplicates:
                self.report.error(
                    "workflow.duplicate-variable",
                    f"{field} has duplicate names: {duplicates}.",
                    location,
                )
            for index, variable in enumerate(raw_variables):
                item_path = f"{location}[{index}]"
                if not isinstance(variable, dict):
                    self.report.error("workflow.variable", "Variable item must be a mapping.", item_path)
                elif not variable.get("name") or not variable.get("value_type"):
                    self.report.warn("workflow.variable-field", "Variable is missing name or value_type.", item_path)

    def _validate_references(self) -> None:
        seen: set[tuple[str, tuple[str, ...]]] = set()
        for path, key, value in _walk(self.workflow):
            if isinstance(value, str):
                for match in VAR_REF_RE.finditer(value):
                    selector = tuple(match.group(1).split("."))
                    marker = (path, selector)
                    if marker not in seen:
                        seen.add(marker)
                        self._validate_selector(selector, path)
            is_selector_key = key == "selector" or key.endswith("_selector") or key in {"query", "variable"}
            if is_selector_key and isinstance(value, list):
                if len(value) >= 2 and all(isinstance(part, str) for part in value):
                    selector = tuple(value)
                    marker = (path, selector)
                    if marker not in seen:
                        seen.add(marker)
                        self._validate_selector(selector, path)
            if key == "variables" and isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, list) and len(item) >= 2 and all(isinstance(part, str) for part in item):
                        selector = tuple(item)
                        marker = (f"{path}[{index}]", selector)
                        if marker not in seen:
                            seen.add(marker)
                            self._validate_selector(selector, marker[0])

    def _validate_selector(self, selector: tuple[str, ...], location: str) -> None:
        if len(selector) < 2:
            # Human Input delivery templates can contain local one-part fields
            # such as {{#url#}}; they are not workflow variable selectors.
            return
        root, output_name = selector[0], selector[1]
        if root in SYSTEM_ROOTS:
            return
        if root not in self.node_type_by_id:
            self.report.error(
                "reference.unknown-root",
                f"Variable selector references unknown node/root {root!r}.",
                location,
            )
            return
        known_outputs = self.output_names_by_node.get(root)
        if known_outputs is not None and output_name not in known_outputs:
            self.report.error(
                "reference.unknown-output",
                f"Node {root!r} does not declare output {output_name!r}; known outputs: {sorted(known_outputs)}.",
                location,
            )

    def _validate_dependencies(self) -> None:
        raw_dependencies = self.document.get("dependencies", [])
        if not isinstance(raw_dependencies, list):
            self.report.error("dependency.type", "Top-level dependencies must be a list.", "dependencies")
            raw_dependencies = []

        provided: set[str] = set()
        for index, dependency in enumerate(raw_dependencies):
            location = f"dependencies[{index}]"
            if not isinstance(dependency, dict):
                self.report.error("dependency.item", "Dependency item must be a mapping.", location)
                continue
            dependency_type = dependency.get("type")
            value = dependency.get("value")
            if dependency_type not in DEPENDENCY_TYPES:
                self.report.error(
                    "dependency.unsupported-type",
                    f"Unsupported dependency type {dependency_type!r}.",
                    f"{location}.type",
                )
                continue
            if not isinstance(value, dict):
                self.report.error("dependency.value", "Dependency value must be a mapping.", f"{location}.value")
                continue
            identifier: Any = None
            if dependency_type == "marketplace":
                identifier = value.get("marketplace_plugin_unique_identifier")
                if not identifier:
                    self.report.error(
                        "dependency.identifier",
                        "Marketplace dependency is missing marketplace_plugin_unique_identifier.",
                        f"{location}.value",
                    )
            elif dependency_type == "package":
                identifier = value.get("plugin_unique_identifier")
                if not identifier:
                    self.report.error(
                        "dependency.identifier",
                        "Package dependency is missing plugin_unique_identifier.",
                        f"{location}.value",
                    )
            else:
                fields = ("repo", "version", "package", "github_plugin_unique_identifier")
                missing = [key for key in fields if not value.get(key)]
                if missing:
                    self.report.error(
                        "dependency.github-fields",
                        f"GitHub dependency is missing fields: {missing}.",
                        f"{location}.value",
                    )
                identifier = value.get("github_plugin_unique_identifier") or value.get("package")
            normalized = _plugin_id(identifier)
            if normalized:
                if normalized in provided:
                    self.report.warn("dependency.duplicate", f"Duplicate dependency for {normalized!r}.", location)
                provided.add(normalized)

        required: dict[str, set[str]] = defaultdict(set)
        for node_id, node in self.node_by_id.items():
            data = _dict(node.get("data"))
            node_type = data.get("type")
            candidates: list[Any] = []
            if node_type in {"llm", "question-classifier", "parameter-extractor"}:
                candidates.append(_dict(data.get("model")).get("provider"))
            elif node_type == "tool" and data.get("provider_type") not in {"workflow", "api", "mcp"}:
                candidates.extend((data.get("plugin_id"), data.get("provider_id")))
            elif node_type in TRIGGER_TYPES:
                candidates.extend((data.get("plugin_id"), data.get("provider_id")))
            elif node_type in {"agent", "knowledge-retrieval", "knowledge-index", "datasource"}:
                for _, key, value in _walk(data):
                    if key in {"provider", "provider_id", "plugin_id", "agent_strategy_provider_name"}:
                        candidates.append(value)
            for candidate in candidates:
                if normalized := _plugin_id(candidate):
                    required[normalized].add(f"node {node_id}")

        for package_ref, package in self.agent_packages.items():
            for path, key, value in _walk(package, f"agent_packages.{package_ref}"):
                if key in {"provider", "provider_id", "plugin_id"}:
                    if normalized := _plugin_id(value):
                        required[normalized].add(path)

        model_config = self.document.get("model_config")
        if isinstance(model_config, dict):
            for path, key, value in _walk(model_config, "model_config"):
                if key in {"provider", "provider_id", "plugin_id"}:
                    if normalized := _plugin_id(value):
                        required[normalized].add(path)

        for missing in sorted(set(required) - provided):
            sources = ", ".join(sorted(required[missing]))
            self.report.error(
                "dependency.missing",
                f"Referenced plugin {missing!r} has no matching top-level dependency (used by {sources}).",
                "dependencies",
            )


def validate_document(
    document: Any,
    *,
    path: Path | str = Path("<memory>"),
    target_version: str | None = None,
) -> Report:
    """Validate an already parsed YAML document."""

    return Validator(document, Path(path), target_version=target_version).run()


def validate_path(path: Path | str, target_version: str | None = None) -> Report:
    """Load and validate one YAML file without raising for user-facing errors."""

    resolved_path = Path(path)
    report = Report(resolved_path)
    try:
        source = resolved_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.error("file.read", f"Could not read file: {exc}", str(resolved_path))
        return report
    try:
        document = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        report.error("yaml.parse", f"YAML parse failed: {exc}", str(resolved_path))
        return report
    return validate_document(document, path=resolved_path, target_version=target_version)


# Backward-compatible library name used by early adopters of the script.
validate_file = validate_path
