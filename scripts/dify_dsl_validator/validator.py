"""Version-aware structural validator for portable Dify App DSL files."""

from __future__ import annotations

import re
from collections import defaultdict, deque
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
CONTAINER_TYPES = {"iteration", "loop"}
CONTAINER_START_TYPES = {"iteration": "iteration-start", "loop": "loop-start"}

AGENT_PACKAGE_FIELDS = {"schema_version", "metadata", "soul", "omitted_assets"}
AGENT_METADATA_FIELDS = {
    "name",
    "description",
    "role",
    "icon_type",
    "icon",
    "icon_background",
}
AGENT_OMITTED_ASSET_FIELDS = {"kind", "name", "size", "hash", "mime_type"}
AGENT_SOUL_FIELDS = {
    "schema_version",
    "prompt",
    "tools",
    "knowledge",
    "human",
    "env",
    "config_skills",
    "config_files",
    "config_note",
    "files",
    "sandbox",
    "memory",
    "model",
    "app_features",
    "app_variables",
    "misc_legacy",
}
AGENT_SOUL_MAPPING_FIELDS = {
    "prompt",
    "tools",
    "knowledge",
    "human",
    "env",
    "files",
    "sandbox",
    "memory",
    "app_features",
    "misc_legacy",
}
AGENT_SOUL_LIST_FIELDS = {"config_skills", "config_files", "app_variables"}
AGENT_SOUL_KNOWLEDGE_FIELDS = {"sets"}
AGENT_KNOWLEDGE_SET_FIELDS = {
    "id",
    "name",
    "description",
    "datasets",
    "query",
    "retrieval",
    "metadata_filtering",
}
AGENT_KNOWLEDGE_DATASET_FIELDS = {"id", "name", "description"}
AGENT_KNOWLEDGE_QUERY_FIELDS = {"mode", "value"}
AGENT_KNOWLEDGE_RETRIEVAL_FIELDS = {
    "mode",
    "top_k",
    "score_threshold",
    "reranking_mode",
    "reranking_enable",
    "reranking_model",
    "weights",
    "model",
}
AGENT_KNOWLEDGE_RERANKING_MODEL_FIELDS = {"provider", "model"}
AGENT_KNOWLEDGE_MODEL_FIELDS = {"provider", "name", "mode", "completion_params"}
AGENT_KNOWLEDGE_METADATA_FIELDS = {"mode", "model_config", "conditions"}
AGENT_CONFIG_SKILL_FIELDS = {
    "name",
    "description",
    "file_kind",
    "file_id",
    "is_missing",
    "size",
    "hash",
    "mime_type",
}
AGENT_CONFIG_FILE_FIELDS = {
    "name",
    "file_kind",
    "file_id",
    "is_missing",
    "size",
    "hash",
    "mime_type",
}
AGENT_JOB_FIELDS = {
    "schema_version",
    "mode",
    "workflow_prompt",
    "previous_node_output_refs",
    "declared_outputs",
    "human_contacts",
    "metadata",
}
AGENT_JOB_MODES = {"let_agent_figure_it_out", "tell_agent_what_to_do"}
DECLARED_OUTPUT_FIELDS = {
    "id",
    "name",
    "type",
    "description",
    "required",
    "file",
    "array_item",
    "children",
    "check",
    "failure_strategy",
}
DECLARED_OUTPUT_TYPES = {"string", "number", "object", "array", "boolean", "file"}
DECLARED_OUTPUT_FILE_FIELDS = {"extensions", "mime_types"}
DECLARED_ARRAY_ITEM_FIELDS = {"type", "description", "children"}
DECLARED_OUTPUT_CHILD_FIELDS = {
    "name",
    "type",
    "description",
    "required",
    "file",
    "array_item",
    "children",
}
DECLARED_OUTPUT_CHECK_FIELDS = {
    "enabled",
    "prompt",
    "benchmark_file_ref",
    "model_ref",
}
DECLARED_OUTPUT_FAILURE_FIELDS = {"retry", "on_failure", "default_value"}
DECLARED_OUTPUT_RETRY_FIELDS = {"enabled", "max_retries", "retry_interval_ms"}
DECLARED_OUTPUT_FAILURE_MODES = {"stop", "default_value", "fail_branch"}
HUMAN_INPUT_TYPES = {"paragraph", "select", "file", "file-list"}
HUMAN_VALUE_SOURCE_TYPES = {"constant", "variable"}
HUMAN_FILE_TYPES = {"image", "document", "audio", "video", "custom"}
HUMAN_FILE_UPLOAD_METHODS = {"local_file", "remote_url"}
NON_SELECTOR_LIST_KEYS = {
    "default",
    "options",
    "allowed_file_types",
    "allowed_file_extensions",
    "allowed_file_upload_methods",
    "extensions",
    "mime_types",
    "stop",
    "tags",
    "choices",
    "enum",
    "recipients",
    "install_commands",
}
SELECTOR_COLLECTION_KEYS = {"variables"}

VAR_REF_RE = re.compile(r"\{\{#([^#{}]+)#\}\}")
HUMAN_OUTPUT_RE = re.compile(r"\{\{#\$output\.([A-Za-z_][A-Za-z0-9_]{0,29})#\}\}")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CONFIG_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
NODE_ID_RE = re.compile(r"^[A-Za-z0-9_:-]+$")
RUNTIME_TEMPLATE_NODE_ID_RE = re.compile(r"^[A-Za-z0-9_]{1,50}$")
SQL_DESTRUCTIVE_RE = re.compile(r"\b(drop|truncate|alter)\b", re.IGNORECASE)
SQL_MUTATING_RE = re.compile(r"\b(delete|update|insert|merge|replace)\b", re.IGNORECASE)
SQL_TRAILING_COMMA_RE = re.compile(r"\([^;]*,\s*\)", re.IGNORECASE | re.DOTALL)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _duplicates(values: Iterable[Any]) -> list[Any]:
    """Return duplicate YAML values without assuming they are hashable."""

    counts: dict[tuple[str, str], tuple[Any, int]] = {}
    for value in values:
        if value is None or value == "":
            continue
        marker = (type(value).__name__, repr(value))
        original, count = counts.get(marker, (value, 0))
        counts[marker] = (original, count + 1)
    return sorted((value for value, count in counts.values() if count > 1), key=repr)


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _unexpected_fields(value: dict[str, Any], allowed: set[str]) -> list[str]:
    return sorted(str(key) for key in value if key not in allowed)


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
            self._validate_containers()
            self._validate_graph_shape()
            self._validate_branch_coverage()
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
            for field in _unexpected_fields(raw_package, AGENT_PACKAGE_FIELDS):
                self.report.error(
                    "agent.package-extra-field",
                    f"Agent package field {field!r} is not allowed by Dify 1.16.",
                    f"{location}.{field}",
                )
            schema_version = raw_package.get("schema_version", 1)
            if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
                self.report.error(
                    "agent.package-schema",
                    "Agent package schema_version must be 1.",
                    f"{location}.schema_version",
                )
            metadata = raw_package.get("metadata")
            if not isinstance(metadata, dict):
                self.report.error(
                    "agent.package-metadata",
                    "Agent package metadata must be a mapping.",
                    f"{location}.metadata",
                )
            else:
                for field in _unexpected_fields(metadata, AGENT_METADATA_FIELDS):
                    self.report.error(
                        "agent.package-extra-field",
                        f"Agent package metadata field {field!r} is not allowed by Dify 1.16.",
                        f"{location}.metadata.{field}",
                    )
                name = metadata.get("name")
                if not isinstance(name, str) or not name or len(name) > 255:
                    self.report.error(
                        "agent.package-metadata",
                        "Agent package metadata.name must contain 1-255 characters.",
                        f"{location}.metadata.name",
                    )
                for field in ("description", "role"):
                    value = metadata.get(field, "")
                    if not isinstance(value, str):
                        self.report.error(
                            "agent.package-metadata-field",
                            f"Agent package metadata.{field} must be a string.",
                            f"{location}.metadata.{field}",
                        )
                for field in ("icon_type", "icon", "icon_background"):
                    value = metadata.get(field)
                    if value is not None and not isinstance(value, str):
                        self.report.error(
                            "agent.package-metadata-field",
                            f"Agent package metadata.{field} must be a string or null.",
                            f"{location}.metadata.{field}",
                        )
            soul = raw_package.get("soul")
            if not isinstance(soul, dict):
                self.report.error("agent.package-soul", "Agent package soul must be a mapping.", f"{location}.soul")
            else:
                self._validate_agent_soul(soul, f"{location}.soul")
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
                    if not isinstance(asset, dict):
                        self.report.error(
                            "agent.omitted-asset",
                            "Each omitted asset must be a mapping.",
                            asset_path,
                        )
                        continue
                    for field in _unexpected_fields(asset, AGENT_OMITTED_ASSET_FIELDS):
                        self.report.error(
                            "agent.package-extra-field",
                            f"Omitted asset field {field!r} is not allowed by Dify 1.16.",
                            f"{asset_path}.{field}",
                        )
                    kind = asset.get("kind")
                    if not isinstance(kind, str) or kind not in {"skill", "file"}:
                        self.report.error(
                            "agent.omitted-asset",
                            "Omitted asset kind must be 'skill' or 'file'.",
                            f"{asset_path}.kind",
                        )
                    if not isinstance(asset.get("name"), str):
                        self.report.error(
                            "agent.omitted-asset",
                            "Omitted asset name must be a string.",
                            f"{asset_path}.name",
                        )
                    size = asset.get("size")
                    if size is not None and (not isinstance(size, int) or isinstance(size, bool)):
                        self.report.error(
                            "agent.omitted-asset-field",
                            "Omitted asset size must be an integer or null.",
                            f"{asset_path}.size",
                        )
                    for field in ("hash", "mime_type"):
                        value = asset.get(field)
                        if value is not None and not isinstance(value, str):
                            self.report.error(
                                "agent.omitted-asset-field",
                                f"Omitted asset {field} must be a string or null.",
                                f"{asset_path}.{field}",
                            )

    def _validate_agent_soul(self, soul: dict[str, Any], location: str) -> None:
        for field in _unexpected_fields(soul, AGENT_SOUL_FIELDS):
            self.report.error(
                "agent.soul-extra-field",
                f"AgentSoulConfig field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        schema_version = soul.get("schema_version", 1)
        if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
            self.report.error(
                "agent.soul-schema",
                "Agent soul schema_version must be integer 1.",
                f"{location}.schema_version",
            )
        for field in AGENT_SOUL_MAPPING_FIELDS:
            if field in soul and not isinstance(soul[field], dict):
                self.report.error(
                    "agent.soul-field-type",
                    f"AgentSoulConfig {field} must be a mapping.",
                    f"{location}.{field}",
                )
        for field in AGENT_SOUL_LIST_FIELDS:
            if field in soul and not isinstance(soul[field], list):
                self.report.error(
                    "agent.soul-field-type",
                    f"AgentSoulConfig {field} must be a list.",
                    f"{location}.{field}",
                )
        if "config_note" in soul and not isinstance(soul["config_note"], str):
            self.report.error(
                "agent.soul-field-type",
                "AgentSoulConfig config_note must be a string.",
                f"{location}.config_note",
            )
        model = soul.get("model")
        if model is not None and not isinstance(model, dict):
            self.report.error(
                "agent.soul-field-type",
                "AgentSoulConfig model must be a mapping or null.",
                f"{location}.model",
            )
        elif isinstance(model, dict):
            self._validate_agent_soul_model(model, f"{location}.model")

        knowledge = soul.get("knowledge")
        if isinstance(knowledge, dict):
            self._validate_agent_soul_knowledge(knowledge, f"{location}.knowledge")

        for field, allowed_fields, kind in (
            ("config_skills", AGENT_CONFIG_SKILL_FIELDS, "skill"),
            ("config_files", AGENT_CONFIG_FILE_FIELDS, "file"),
        ):
            values = soul.get(field)
            if isinstance(values, list):
                self._validate_agent_config_assets(
                    values,
                    f"{location}.{field}",
                    allowed_fields=allowed_fields,
                    kind=kind,
                )

    def _validate_agent_soul_model(self, model: dict[str, Any], location: str) -> None:
        for field in ("plugin_id", "model_provider", "model"):
            value = model.get(field)
            if not isinstance(value, str) or not value or len(value) > 255:
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent soul model {field} must contain 1-255 characters.",
                    f"{location}.{field}",
                )
        credential_ref = model.get("credential_ref")
        if credential_ref is not None:
            if not isinstance(credential_ref, dict):
                self.report.error(
                    "agent.soul-field-type",
                    "Agent soul model credential_ref must be a mapping or null.",
                    f"{location}.credential_ref",
                )
            else:
                credential_type = credential_ref.get("type")
                if (
                    not isinstance(credential_type, str)
                    or not credential_type
                    or len(credential_type) > 64
                ):
                    self.report.error(
                        "agent.soul-field-type",
                        "Agent soul model credential_ref.type must contain 1-64 characters.",
                        f"{location}.credential_ref.type",
                    )
                for field in ("id", "provider"):
                    value = credential_ref.get(field)
                    if value is not None and (not isinstance(value, str) or len(value) > 255):
                        self.report.error(
                            "agent.soul-field-type",
                            f"Agent soul model credential_ref.{field} must be a string of at most 255 characters or null.",
                            f"{location}.credential_ref.{field}",
                        )
        if "model_settings" in model and not isinstance(model["model_settings"], dict):
            self.report.error(
                "agent.soul-field-type",
                "Agent soul model model_settings must be a mapping.",
                f"{location}.model_settings",
            )

    def _validate_agent_soul_knowledge(self, knowledge: dict[str, Any], location: str) -> None:
        for field in _unexpected_fields(knowledge, AGENT_SOUL_KNOWLEDGE_FIELDS):
            self.report.error(
                "agent.soul-extra-field",
                f"Agent soul knowledge field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        sets = knowledge.get("sets", [])
        if not isinstance(sets, list):
            self.report.error(
                "agent.soul-field-type",
                "Agent soul knowledge.sets must be a list.",
                f"{location}.sets",
            )
            return

        set_ids: list[str] = []
        set_names: list[str] = []
        for index, item in enumerate(sets):
            item_path = f"{location}.sets[{index}]"
            if not isinstance(item, dict):
                self.report.error(
                    "agent.soul-field-type",
                    "Each Agent knowledge set must be a mapping.",
                    item_path,
                )
                continue
            for field in _unexpected_fields(item, AGENT_KNOWLEDGE_SET_FIELDS):
                self.report.error(
                    "agent.soul-extra-field",
                    f"Agent knowledge set field {field!r} is not allowed by Dify 1.16.",
                    f"{item_path}.{field}",
                )
            for field in ("id", "name"):
                value = item.get(field)
                if (
                    not isinstance(value, str)
                    or not value.strip()
                    or len(value) > 255
                ):
                    self.report.error(
                        "agent.soul-field-type",
                        f"Agent knowledge set {field} must contain 1-255 non-blank characters.",
                        f"{item_path}.{field}",
                    )
                elif field == "id":
                    set_ids.append(value.strip())
                else:
                    set_names.append(value.strip().lower())
            description = item.get("description")
            if description is not None and not isinstance(description, str):
                self.report.error(
                    "agent.soul-field-type",
                    "Agent knowledge set description must be a string or null.",
                    f"{item_path}.description",
                )
            self._validate_agent_knowledge_datasets(item.get("datasets"), f"{item_path}.datasets")
            self._validate_agent_knowledge_query(item.get("query"), f"{item_path}.query")
            self._validate_agent_knowledge_retrieval(item.get("retrieval"), f"{item_path}.retrieval")
            metadata_filtering = item.get("metadata_filtering", {})
            if not isinstance(metadata_filtering, dict):
                self.report.error(
                    "agent.soul-field-type",
                    "Agent knowledge metadata_filtering must be a mapping.",
                    f"{item_path}.metadata_filtering",
                )
            else:
                for field in _unexpected_fields(metadata_filtering, AGENT_KNOWLEDGE_METADATA_FIELDS):
                    self.report.error(
                        "agent.soul-extra-field",
                        f"Agent knowledge metadata_filtering field {field!r} is not allowed by Dify 1.16.",
                        f"{item_path}.metadata_filtering.{field}",
                    )
                mode = metadata_filtering.get("mode", "disabled")
                if not isinstance(mode, str) or mode not in {"disabled", "automatic", "manual"}:
                    self.report.error(
                        "agent.soul-field-type",
                        "Agent knowledge metadata_filtering.mode must be disabled, automatic, or manual.",
                        f"{item_path}.metadata_filtering.mode",
                    )
                for field in ("model_config", "conditions"):
                    value = metadata_filtering.get(field)
                    if value is not None and not isinstance(value, dict):
                        self.report.error(
                            "agent.soul-field-type",
                            f"Agent knowledge metadata_filtering.{field} must be a mapping or null.",
                            f"{item_path}.metadata_filtering.{field}",
                        )

        if len(set_ids) != len(set(set_ids)):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge set ids must be unique.",
                f"{location}.sets",
            )
        if len(set_names) != len(set(set_names)):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge set names must be unique case-insensitively.",
                f"{location}.sets",
            )

    def _validate_agent_knowledge_datasets(self, value: Any, location: str) -> None:
        if not isinstance(value, list) or not value:
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge set datasets must be a non-empty list.",
                location,
            )
            return
        dataset_ids: list[str] = []
        for index, dataset in enumerate(value):
            item_path = f"{location}[{index}]"
            if not isinstance(dataset, dict):
                self.report.error(
                    "agent.soul-field-type",
                    "Agent knowledge dataset must be a mapping.",
                    item_path,
                )
                continue
            for field in _unexpected_fields(dataset, AGENT_KNOWLEDGE_DATASET_FIELDS):
                self.report.error(
                    "agent.soul-extra-field",
                    f"Agent knowledge dataset field {field!r} is not allowed by Dify 1.16.",
                    f"{item_path}.{field}",
                )
            dataset_id = dataset.get("id")
            if (
                not isinstance(dataset_id, str)
                or not dataset_id.strip()
                or len(dataset_id) > 255
            ):
                self.report.error(
                    "agent.soul-field-type",
                    "Agent knowledge dataset id must contain 1-255 non-blank characters.",
                    f"{item_path}.id",
                )
            else:
                dataset_ids.append(dataset_id.strip())
            name = dataset.get("name")
            if name is not None and (not isinstance(name, str) or len(name) > 255):
                self.report.error(
                    "agent.soul-field-type",
                    "Agent knowledge dataset name must be a string of at most 255 characters or null.",
                    f"{item_path}.name",
                )
            description = dataset.get("description")
            if description is not None and not isinstance(description, str):
                self.report.error(
                    "agent.soul-field-type",
                    "Agent knowledge dataset description must be a string or null.",
                    f"{item_path}.description",
                )
        if len(dataset_ids) != len(set(dataset_ids)):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge dataset ids must be unique within a set.",
                location,
            )

    def _validate_agent_knowledge_query(self, value: Any, location: str) -> None:
        if not isinstance(value, dict):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge set query must be a mapping.",
                location,
            )
            return
        for field in _unexpected_fields(value, AGENT_KNOWLEDGE_QUERY_FIELDS):
            self.report.error(
                "agent.soul-extra-field",
                f"Agent knowledge query field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        mode = value.get("mode")
        if not isinstance(mode, str) or mode not in {"user_query", "generated_query"}:
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge query.mode must be user_query or generated_query.",
                f"{location}.mode",
            )
        query_value = value.get("value")
        if query_value is not None and not isinstance(query_value, str):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge query.value must be a string or null.",
                f"{location}.value",
            )

    def _validate_agent_knowledge_retrieval(self, value: Any, location: str) -> None:
        if not isinstance(value, dict):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge set retrieval must be a mapping.",
                location,
            )
            return
        for field in _unexpected_fields(value, AGENT_KNOWLEDGE_RETRIEVAL_FIELDS):
            self.report.error(
                "agent.soul-extra-field",
                f"Agent knowledge retrieval field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        mode = value.get("mode")
        if not isinstance(mode, str) or mode not in {"single", "multiple"}:
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge retrieval.mode must be single or multiple.",
                f"{location}.mode",
            )
        top_k = value.get("top_k")
        if top_k is not None and (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k < 1
        ):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge retrieval.top_k must be an integer greater than zero or null.",
                f"{location}.top_k",
            )
        score_threshold = value.get("score_threshold")
        if score_threshold is not None and (
            not isinstance(score_threshold, (int, float))
            or isinstance(score_threshold, bool)
            or not 0 <= score_threshold <= 1
        ):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge retrieval.score_threshold must be between 0 and 1 or null.",
                f"{location}.score_threshold",
            )
        if "reranking_mode" in value and not isinstance(value["reranking_mode"], str):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge retrieval.reranking_mode must be a string.",
                f"{location}.reranking_mode",
            )
        if "reranking_enable" in value and not isinstance(value["reranking_enable"], bool):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge retrieval.reranking_enable must be a boolean.",
                f"{location}.reranking_enable",
            )
        self._validate_agent_knowledge_named_model(
            value.get("reranking_model"),
            f"{location}.reranking_model",
            allowed_fields=AGENT_KNOWLEDGE_RERANKING_MODEL_FIELDS,
            required_fields=("provider", "model"),
        )
        self._validate_agent_knowledge_named_model(
            value.get("model"),
            f"{location}.model",
            allowed_fields=AGENT_KNOWLEDGE_MODEL_FIELDS,
            required_fields=("provider", "name", "mode"),
        )
        weights = value.get("weights")
        if weights is not None and not isinstance(weights, dict):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge retrieval.weights must be a mapping or null.",
                f"{location}.weights",
            )

    def _validate_agent_knowledge_named_model(
        self,
        value: Any,
        location: str,
        *,
        allowed_fields: set[str],
        required_fields: tuple[str, ...],
    ) -> None:
        if value is None:
            return
        if not isinstance(value, dict):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge model config must be a mapping or null.",
                location,
            )
            return
        for field in _unexpected_fields(value, allowed_fields):
            self.report.error(
                "agent.soul-extra-field",
                f"Agent knowledge model field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        for field in required_fields:
            field_value = value.get(field)
            limit = 64 if field == "mode" else 255
            if (
                not isinstance(field_value, str)
                or not field_value
                or len(field_value) > limit
            ):
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent knowledge model {field} must contain 1-{limit} characters.",
                    f"{location}.{field}",
                )
        if "completion_params" in value and not isinstance(value["completion_params"], dict):
            self.report.error(
                "agent.soul-field-type",
                "Agent knowledge model completion_params must be a mapping.",
                f"{location}.completion_params",
            )

    def _validate_agent_config_assets(
        self,
        values: list[Any],
        location: str,
        *,
        allowed_fields: set[str],
        kind: str,
    ) -> None:
        for index, item in enumerate(values):
            item_path = f"{location}[{index}]"
            if not isinstance(item, dict):
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent config {kind} must be a mapping.",
                    item_path,
                )
                continue
            for field in _unexpected_fields(item, allowed_fields):
                self.report.error(
                    "agent.soul-extra-field",
                    f"Agent config {kind} field {field!r} is not allowed by Dify 1.16.",
                    f"{item_path}.{field}",
                )
            name = item.get("name")
            valid_name = (
                isinstance(name, str)
                and bool(name.strip())
                and len(name) <= 255
                and name not in {".", ".."}
                and "/" not in name
                and "\\" not in name
                and "\x00" not in name
                and not any(ord(char) < 0x20 for char in name)
            )
            if kind == "skill" and valid_name:
                valid_name = CONFIG_SKILL_NAME_RE.fullmatch(name.strip()) is not None
            if not valid_name:
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent config {kind} name is invalid.",
                    f"{item_path}.name",
                )
            file_kind = item.get("file_kind", "tool_file" if kind == "skill" else None)
            allowed_kinds = {"tool_file"} if kind == "skill" else {"upload_file", "tool_file"}
            if not isinstance(file_kind, str) or file_kind not in allowed_kinds:
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent config {kind} file_kind must be one of {sorted(allowed_kinds)}.",
                    f"{item_path}.file_kind",
                )
            file_id = item.get("file_id", "")
            if not isinstance(file_id, str) or len(file_id) > 255:
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent config {kind} file_id must be a string of at most 255 characters.",
                    f"{item_path}.file_id",
                )
            is_missing = item.get("is_missing", False)
            if not isinstance(is_missing, bool):
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent config {kind} is_missing must be a boolean.",
                    f"{item_path}.is_missing",
                )
            elif isinstance(file_id, str):
                if is_missing and file_id:
                    self.report.error(
                        "agent.soul-field-type",
                        f"Missing Agent config {kind} must not retain file_id.",
                        f"{item_path}.file_id",
                    )
                elif not is_missing and not file_id.strip():
                    self.report.error(
                        "agent.soul-field-type",
                        f"Agent config {kind} file_id is required unless is_missing is true.",
                        f"{item_path}.file_id",
                    )
            size = item.get("size")
            if size is not None and (not isinstance(size, int) or isinstance(size, bool)):
                self.report.error(
                    "agent.soul-field-type",
                    f"Agent config {kind} size must be an integer or null.",
                    f"{item_path}.size",
                )
            for field in ("description", "hash", "mime_type"):
                if field not in allowed_fields:
                    continue
                value = item.get(field)
                if value is not None and not isinstance(value, str):
                    self.report.error(
                        "agent.soul-field-type",
                        f"Agent config {kind} {field} must be a string or null.",
                        f"{item_path}.{field}",
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
            if not isinstance(wrapper_type, str):
                self.report.error(
                    "node.wrapper-type",
                    "Node wrapper type must be a string.",
                    f"{location}.type",
                )
            elif wrapper_type not in WRAPPER_TYPES:
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
                self.report.error(
                    "node.llm.model",
                    f"LLM node {title!r} requires an explicit model provider and name.",
                    f"{location}.model",
                )
            elif not isinstance(model.get("mode"), str) or not model.get("mode"):
                self.report.error(
                    "node.llm.model",
                    f"LLM node {title!r} requires model.mode.",
                    f"{location}.model.mode",
                )
            if not isinstance(data.get("prompt_template"), list):
                self.report.error(
                    "node.llm.prompt",
                    "LLM prompt_template must be a list.",
                    f"{location}.prompt_template",
                )
            context = data.get("context")
            if not isinstance(context, dict) or not isinstance(context.get("enabled"), bool):
                self.report.error(
                    "node.llm.context",
                    "LLM context must be a mapping with a boolean enabled field.",
                    f"{location}.context",
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
        elif node_type == "iteration":
            # Dify exposes the current item and index to nodes inside the
            # iteration in addition to the aggregate output visible outside.
            outputs = {"output", "item", "index"}
        elif node_type == "loop":
            outputs = {"output"}
            for variable in _list(data.get("loop_variables")):
                if not isinstance(variable, dict):
                    continue
                label = variable.get("label")
                if isinstance(label, str) and label:
                    outputs.add(label)
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
        timeout_unit = data.get("timeout_unit")
        if not isinstance(timeout_unit, str) or timeout_unit not in {"hour", "day"}:
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
            input_type = item.get("type")
            if not isinstance(input_type, str) or input_type not in HUMAN_INPUT_TYPES:
                self.report.error(
                    "node.human-input.input-type",
                    "Input type must be paragraph, select, file, or file-list.",
                    f"{item_path}.type",
                )
                continue
            if input_type == "paragraph":
                default = item.get("default")
                if default is not None:
                    self._validate_human_value_source(
                        default,
                        f"{item_path}.default",
                        list_value=False,
                        code="node.human-input.default",
                    )
            elif input_type == "select":
                option_source = item.get("option_source")
                if option_source is None:
                    self.report.error(
                        "node.human-input.option-source",
                        "Select input requires option_source.",
                        f"{item_path}.option_source",
                    )
                else:
                    self._validate_human_value_source(
                        option_source,
                        f"{item_path}.option_source",
                        list_value=True,
                        code="node.human-input.option-source",
                    )
            else:
                self._validate_human_file_input(item, item_path, is_list=input_type == "file-list")

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
            button_style = action.get("button_style", "default")
            if not isinstance(button_style, str) or button_style not in {"primary", "default", "accent", "ghost"}:
                self.report.error(
                    "node.human-input.button-style",
                    "button_style must be primary, default, accent, or ghost.",
                    f"{action_path}.button_style",
                )
        return outputs

    def _validate_human_value_source(
        self,
        source: Any,
        location: str,
        *,
        list_value: bool,
        code: str,
    ) -> None:
        if not isinstance(source, dict):
            self.report.error(code, "Value source must be a mapping.", location)
            return
        source_type = source.get("type")
        if not isinstance(source_type, str) or source_type not in HUMAN_VALUE_SOURCE_TYPES:
            self.report.error(
                code,
                "Value source type must be constant or variable.",
                f"{location}.type",
            )
        selector = source.get("selector", [])
        if not _is_string_list(selector):
            self.report.error(
                code,
                "Value source selector must be a list of strings.",
                f"{location}.selector",
            )
        elif source_type == "variable" and len(selector) < 2:
            self.report.error(
                code,
                "Variable value source selector must contain at least two strings.",
                f"{location}.selector",
            )
        value = source.get("value", [] if list_value else "")
        valid_value = _is_string_list(value) if list_value else isinstance(value, str)
        if not valid_value:
            expected = "a list of strings" if list_value else "a string"
            self.report.error(code, f"Constant value must be {expected}.", f"{location}.value")

    def _validate_human_file_input(self, item: dict[str, Any], location: str, *, is_list: bool) -> None:
        allowed_types = item.get("allowed_file_types", [])
        if not _is_string_list(allowed_types) or any(value not in HUMAN_FILE_TYPES for value in allowed_types):
            self.report.error(
                "node.human-input.file-config",
                "allowed_file_types must contain only image, document, audio, video, or custom.",
                f"{location}.allowed_file_types",
            )
        extensions = item.get("allowed_file_extensions", [])
        if not _is_string_list(extensions):
            self.report.error(
                "node.human-input.file-config",
                "allowed_file_extensions must be a list of strings.",
                f"{location}.allowed_file_extensions",
            )
        elif isinstance(allowed_types, list) and "custom" in allowed_types and not extensions:
            self.report.error(
                "node.human-input.file-config",
                "Custom file types require at least one allowed_file_extension.",
                f"{location}.allowed_file_extensions",
            )
        upload_methods = item.get("allowed_file_upload_methods", [])
        if not _is_string_list(upload_methods) or any(
            value not in HUMAN_FILE_UPLOAD_METHODS for value in upload_methods
        ):
            self.report.error(
                "node.human-input.file-config",
                "allowed_file_upload_methods must contain only local_file or remote_url.",
                f"{location}.allowed_file_upload_methods",
            )
        if is_list:
            number_limits = item.get("number_limits", 0)
            if (
                not isinstance(number_limits, int)
                or isinstance(number_limits, bool)
                or number_limits < 0
            ):
                self.report.error(
                    "node.human-input.file-config",
                    "file-list number_limits must be a non-negative integer.",
                    f"{location}.number_limits",
                )

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
            binding_type = binding.get("binding_type")
            if not isinstance(binding_type, str) or binding_type not in {"inline_agent", "roster_agent"}:
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
        for field in _unexpected_fields(job, AGENT_JOB_FIELDS):
            self.report.error(
                "node.agent-v2.job-extra-field",
                f"WorkflowNodeJobConfig field {field!r} is not allowed by Dify 1.16.",
                f"{location}.agent_job.{field}",
            )
        schema_version = job.get("schema_version", 1)
        if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
            self.report.error(
                "node.agent-v2.job-schema",
                "agent_job.schema_version must be integer 1.",
                f"{location}.agent_job.schema_version",
            )
        mode = job.get("mode", "tell_agent_what_to_do")
        if not isinstance(mode, str) or mode not in AGENT_JOB_MODES:
            self.report.error(
                "node.agent-v2.job-field",
                "agent_job.mode must be let_agent_figure_it_out or tell_agent_what_to_do.",
                f"{location}.agent_job.mode",
            )
        if not isinstance(job.get("workflow_prompt", ""), str):
            self.report.error(
                "node.agent-v2.job-field",
                "agent_job.workflow_prompt must be a string.",
                f"{location}.agent_job.workflow_prompt",
            )
        for key in ("previous_node_output_refs", "declared_outputs", "human_contacts"):
            if key in job and not isinstance(job[key], list):
                self.report.error(
                    "node.agent-v2.job-field",
                    f"agent_job.{key} must be a list.",
                    f"{location}.agent_job.{key}",
                )
        for key in ("previous_node_output_refs", "human_contacts"):
            for index, value in enumerate(_list(job.get(key))):
                if not isinstance(value, dict):
                    self.report.error(
                        "node.agent-v2.job-field",
                        f"agent_job.{key} items must be mappings.",
                        f"{location}.agent_job.{key}[{index}]",
                    )
        if not isinstance(job.get("metadata", {}), dict):
            self.report.error(
                "node.agent-v2.job-field",
                "agent_job.metadata must be a mapping.",
                f"{location}.agent_job.metadata",
            )
        declared = _list(job.get("declared_outputs"))
        names: set[str] = set()
        for index, item in enumerate(declared):
            name = self._validate_declared_output(
                item,
                f"{location}.agent_job.declared_outputs[{index}]",
            )
            if name:
                names.add(name)
        return names if declared else {"text", "files", "json"}

    def _validate_declared_output(self, item: Any, location: str, *, child: bool = False) -> str | None:
        if not isinstance(item, dict):
            self.report.error(
                "node.agent-v2.declared-output",
                "Declared output must be a mapping.",
                location,
            )
            return None
        allowed_fields = DECLARED_OUTPUT_CHILD_FIELDS if child else DECLARED_OUTPUT_FIELDS
        for field in _unexpected_fields(item, allowed_fields):
            self.report.error(
                "node.agent-v2.declared-output-extra-field",
                f"Declared output field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )

        name = item.get("name")
        if (
            not isinstance(name, str)
            or not name
            or len(name) > 255
            or not IDENTIFIER_RE.fullmatch(name)
        ):
            self.report.error(
                "node.agent-v2.declared-output-name",
                "Declared output name must be a 1-255 character identifier.",
                f"{location}.name",
            )
            valid_name = None
        else:
            valid_name = name

        output_id = item.get("id")
        if not child and output_id is not None and not isinstance(output_id, str):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output id must be a string or null.",
                f"{location}.id",
            )

        output_type = item.get("type")
        if not isinstance(output_type, str) or output_type not in DECLARED_OUTPUT_TYPES:
            self.report.error(
                "node.agent-v2.declared-output-type",
                f"Declared output type must be one of {sorted(DECLARED_OUTPUT_TYPES)}.",
                f"{location}.type",
            )
            output_type = None

        description = item.get("description")
        if description is not None and not isinstance(description, str):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output description must be a string or null.",
                f"{location}.description",
            )
        if "required" in item and not isinstance(item["required"], bool):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output required must be a boolean.",
                f"{location}.required",
            )

        file_config = item.get("file")
        if file_config is not None:
            if output_type != "file" or not isinstance(file_config, dict):
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "file metadata is allowed only as a mapping for file outputs.",
                    f"{location}.file",
                )
            else:
                for field in _unexpected_fields(file_config, DECLARED_OUTPUT_FILE_FIELDS):
                    self.report.error(
                        "node.agent-v2.declared-output-extra-field",
                        f"Declared output file field {field!r} is not allowed by Dify 1.16.",
                        f"{location}.file.{field}",
                    )
                for field in DECLARED_OUTPUT_FILE_FIELDS:
                    value = file_config.get(field, [])
                    if not _is_string_list(value):
                        self.report.error(
                            "node.agent-v2.declared-output-shape",
                            f"Declared output file {field} must be a list of strings.",
                            f"{location}.file.{field}",
                        )

        array_item = item.get("array_item")
        if array_item is not None:
            if output_type != "array":
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "array_item is allowed only for array outputs.",
                    f"{location}.array_item",
                )
            self._validate_declared_array_item(array_item, f"{location}.array_item")

        children = item.get("children", [])
        if not isinstance(children, list):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output children must be a list.",
                f"{location}.children",
            )
        else:
            if children and output_type != "object":
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "children are allowed only for object outputs.",
                    f"{location}.children",
                )
            for index, value in enumerate(children):
                self._validate_declared_output(value, f"{location}.children[{index}]", child=True)

        if not child:
            check = item.get("check")
            if check is not None:
                self._validate_declared_output_check(
                    check,
                    f"{location}.check",
                    output_type=output_type,
                )
            failure_strategy = item.get("failure_strategy")
            if failure_strategy is not None:
                self._validate_declared_output_failure_strategy(
                    failure_strategy,
                    f"{location}.failure_strategy",
                    output_type=output_type,
                    array_item=array_item,
                )
        return valid_name

    def _validate_declared_output_check(
        self,
        check: Any,
        location: str,
        *,
        output_type: str | None,
    ) -> None:
        if not isinstance(check, dict):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output check must be a mapping or null.",
                location,
            )
            return
        for field in _unexpected_fields(check, DECLARED_OUTPUT_CHECK_FIELDS):
            self.report.error(
                "node.agent-v2.declared-output-extra-field",
                f"Declared output check field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        enabled = check.get("enabled", False)
        if not isinstance(enabled, bool):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output check.enabled must be a boolean.",
                f"{location}.enabled",
            )
            enabled = False
        prompt = check.get("prompt")
        if prompt is not None and not isinstance(prompt, str):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output check.prompt must be a string or null.",
                f"{location}.prompt",
            )
        benchmark = check.get("benchmark_file_ref")
        if benchmark is not None and not isinstance(benchmark, dict):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output check.benchmark_file_ref must be a mapping or null.",
                f"{location}.benchmark_file_ref",
            )
        model_ref = check.get("model_ref")
        if model_ref is not None:
            if not isinstance(model_ref, dict):
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "Declared output check.model_ref must be a mapping or null.",
                    f"{location}.model_ref",
                )
            else:
                self._validate_agent_soul_model(model_ref, f"{location}.model_ref")
        if enabled:
            if output_type != "file":
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "Enabled output checks are allowed only for file outputs.",
                    location,
                )
            if not isinstance(prompt, str) or not prompt.strip():
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "Enabled output checks require a non-blank prompt.",
                    f"{location}.prompt",
                )
            if not isinstance(benchmark, dict):
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "Enabled output checks require benchmark_file_ref.",
                    f"{location}.benchmark_file_ref",
                )

    def _validate_declared_output_failure_strategy(
        self,
        strategy: Any,
        location: str,
        *,
        output_type: str | None,
        array_item: Any,
    ) -> None:
        if not isinstance(strategy, dict):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output failure_strategy must be a mapping or null.",
                location,
            )
            return
        for field in _unexpected_fields(strategy, DECLARED_OUTPUT_FAILURE_FIELDS):
            self.report.error(
                "node.agent-v2.declared-output-extra-field",
                f"Declared output failure_strategy field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        retry = strategy.get("retry", {})
        if not isinstance(retry, dict):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output failure_strategy.retry must be a mapping.",
                f"{location}.retry",
            )
        else:
            for field in _unexpected_fields(retry, DECLARED_OUTPUT_RETRY_FIELDS):
                self.report.error(
                    "node.agent-v2.declared-output-extra-field",
                    f"Declared output retry field {field!r} is not allowed by Dify 1.16.",
                    f"{location}.retry.{field}",
                )
            enabled = retry.get("enabled", False)
            if not isinstance(enabled, bool):
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "Declared output retry.enabled must be a boolean.",
                    f"{location}.retry.enabled",
                )
            for field, maximum in (("max_retries", 10), ("retry_interval_ms", 60_000)):
                value = retry.get(field, 0)
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or not 0 <= value <= maximum
                ):
                    self.report.error(
                        "node.agent-v2.declared-output-shape",
                        f"Declared output retry.{field} must be an integer between 0 and {maximum}.",
                        f"{location}.retry.{field}",
                    )

        on_failure = strategy.get("on_failure", "stop")
        if not isinstance(on_failure, str) or on_failure not in DECLARED_OUTPUT_FAILURE_MODES:
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared output on_failure must be stop, default_value, or fail_branch.",
                f"{location}.on_failure",
            )
            return
        default_value = strategy.get("default_value")
        if on_failure == "default_value":
            if default_value is None:
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "on_failure: default_value requires a non-null default_value.",
                    f"{location}.default_value",
                )
            elif not self._declared_default_matches_type(default_value, output_type, array_item):
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    f"Declared output default_value does not match output type {output_type!r}.",
                    f"{location}.default_value",
                )

    @staticmethod
    def _declared_default_matches_type(value: Any, output_type: str | None, array_item: Any) -> bool:
        if output_type == "string":
            return isinstance(value, str)
        if output_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if output_type == "boolean":
            return isinstance(value, bool)
        if output_type == "object":
            return isinstance(value, dict)
        if output_type == "array":
            if not isinstance(value, list):
                return False
            if isinstance(array_item, dict) and array_item.get("type") == "file":
                return all(Validator._is_valid_file_default(item) for item in value)
            return True
        if output_type == "file":
            return Validator._is_valid_file_default(value)
        return False

    @staticmethod
    def _is_valid_file_default(value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        transfer_method = value.get("transfer_method")
        if transfer_method == "remote_url":
            return (
                set(value) == {"transfer_method", "url"}
                and isinstance(value.get("url"), str)
                and bool(value["url"])
            )
        return (
            isinstance(transfer_method, str)
            and bool(transfer_method)
            and set(value) == {"transfer_method", "reference"}
            and isinstance(value.get("reference"), str)
            and bool(value["reference"])
        )

    def _validate_declared_array_item(self, item: Any, location: str) -> None:
        if not isinstance(item, dict):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "Declared array_item must be a mapping.",
                location,
            )
            return
        for field in _unexpected_fields(item, DECLARED_ARRAY_ITEM_FIELDS):
            self.report.error(
                "node.agent-v2.declared-output-extra-field",
                f"Declared array_item field {field!r} is not allowed by Dify 1.16.",
                f"{location}.{field}",
            )
        item_type = item.get("type")
        if not isinstance(item_type, str) or item_type not in DECLARED_OUTPUT_TYPES or item_type == "array":
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "array_item.type must be a non-array declared output type.",
                f"{location}.type",
            )
            item_type = None
        description = item.get("description")
        if description is not None and not isinstance(description, str):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "array_item.description must be a string or null.",
                f"{location}.description",
            )
        children = item.get("children", [])
        if not isinstance(children, list):
            self.report.error(
                "node.agent-v2.declared-output-shape",
                "array_item.children must be a list.",
                f"{location}.children",
            )
        else:
            if children and item_type != "object":
                self.report.error(
                    "node.agent-v2.declared-output-shape",
                    "array_item.children are allowed only for object array items.",
                    f"{location}.children",
                )
            for index, value in enumerate(children):
                self._validate_declared_output(value, f"{location}.children[{index}]", child=True)

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
        endpoint_pairs: set[tuple[str, str, str]] = set()
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
            source_valid = isinstance(source, str) and bool(source)
            target_valid = isinstance(target, str) and bool(target)
            if not source_valid:
                self.report.error(
                    "edge.endpoint-type",
                    "Edge source must be a non-empty string.",
                    f"{location}.source",
                )
            elif source not in self.node_type_by_id:
                self.report.error("edge.source", f"Edge source {source!r} is not a runtime node.", f"{location}.source")
            if not target_valid:
                self.report.error(
                    "edge.endpoint-type",
                    "Edge target must be a non-empty string.",
                    f"{location}.target",
                )
            elif target not in self.node_type_by_id:
                self.report.error("edge.target", f"Edge target {target!r} is not a runtime node.", f"{location}.target")

            source_handle = edge.get("sourceHandle")
            target_handle = edge.get("targetHandle")
            source_handle_valid = isinstance(source_handle, (str, int, bool))
            target_handle_valid = isinstance(target_handle, (str, int, bool))
            if source_handle is None:
                self.report.warn("edge.source-handle", "Edge is missing sourceHandle.", f"{location}.sourceHandle")
            elif not source_handle_valid:
                self.report.error(
                    "edge.handle-type",
                    "Edge sourceHandle must be a string, integer, or boolean.",
                    f"{location}.sourceHandle",
                )
            if target_handle is None:
                self.report.warn("edge.target-handle", "Edge is missing targetHandle.", f"{location}.targetHandle")
            elif not target_handle_valid:
                self.report.error(
                    "edge.handle-type",
                    "Edge targetHandle must be a string, integer, or boolean.",
                    f"{location}.targetHandle",
                )
            if source_valid and target_valid and source_handle_valid:
                pair = (source, _handle_id(source_handle), target)
                if pair in endpoint_pairs:
                    self.report.warn("edge.duplicate", "Duplicate source/handle/target edge.", location)
                endpoint_pairs.add(pair)

            data = _dict(edge.get("data"))
            source_type = data.get("sourceType")
            target_type = data.get("targetType")
            if source_valid and source in self.node_type_by_id and source_type and source_type != self.node_type_by_id[source]:
                self.report.error(
                    "edge.source-type",
                    f"sourceType {source_type!r} does not match {self.node_type_by_id[source]!r}.",
                    f"{location}.data.sourceType",
                )
            if target_valid and target in self.node_type_by_id and target_type and target_type != self.node_type_by_id[target]:
                self.report.error(
                    "edge.target-type",
                    f"targetType {target_type!r} does not match {self.node_type_by_id[target]!r}.",
                    f"{location}.data.targetType",
                )
            if source_handle is None or source_handle_valid:
                self._validate_branch_handle(edge, location)

    def _validate_branch_handle(self, edge: dict[str, Any], location: str) -> None:
        source = edge.get("source")
        if not isinstance(source, str) or source not in self.node_by_id:
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

    def _declared_branch_handles(self, node_id: str, *, include_timeout: bool) -> set[str] | None:
        node_type = self.node_type_by_id.get(node_id)
        data = _dict(self.node_by_id[node_id].get("data"))
        if node_type == "if-else":
            handles = {"false"}
            for case in _list(data.get("cases")):
                if isinstance(case, dict):
                    value = case.get("case_id", case.get("id"))
                    if value is not None:
                        handles.add(_handle_id(value))
            return handles
        if node_type == "question-classifier":
            return {
                _handle_id(item["id"])
                for item in _list(data.get("classes"))
                if isinstance(item, dict) and item.get("id") is not None
            }
        if node_type == "human-input":
            handles = {
                _handle_id(item["id"])
                for item in _list(data.get("user_actions"))
                if isinstance(item, dict) and item.get("id") is not None
            }
            if include_timeout:
                handles.update({"__timeout", "__timeout__"})
            return handles
        return None

    def _validate_branch_coverage(self) -> None:
        outgoing: dict[str, list[str]] = defaultdict(list)
        for edge in self.edges:
            source = edge.get("source")
            handle = edge.get("sourceHandle")
            if isinstance(source, str) and isinstance(handle, (str, int, bool)):
                outgoing[source].append(_handle_id(handle))

        for node_id in self.node_type_by_id:
            declared = self._declared_branch_handles(node_id, include_timeout=False)
            if declared is None:
                continue
            counts: dict[str, int] = defaultdict(int)
            for handle in outgoing.get(node_id, []):
                counts[handle] += 1
            for handle in sorted(declared):
                if counts[handle] == 0:
                    self.report.warn(
                        "graph.unconnected-branch",
                        f"Declared branch handle {handle!r} on node {node_id!r} has no outgoing edge.",
                        f"workflow.graph.nodes[{node_id}]",
                    )
                elif counts[handle] > 1:
                    self.report.warn(
                        "graph.duplicate-branch-handle",
                        f"Branch handle {handle!r} on node {node_id!r} is used by {counts[handle]} outgoing edges.",
                        f"workflow.graph.nodes[{node_id}]",
                    )

    def _validate_containers(self) -> None:
        container_ids = {
            node_id
            for node_id, node_type in self.node_type_by_id.items()
            if node_type in CONTAINER_TYPES
        }
        parents: dict[str, str] = {}
        children_by_parent: dict[str, list[str]] = defaultdict(list)

        for node_id, node in self.node_by_id.items():
            data = _dict(node.get("data"))
            wrapper_parent = node.get("parentId")
            data_parent = data.get("parentId")
            for field, value, location in (
                ("parentId", wrapper_parent, f"workflow.graph.nodes[{node_id}].parentId"),
                ("data.parentId", data_parent, f"workflow.graph.nodes[{node_id}].data.parentId"),
            ):
                if value is not None and (not isinstance(value, str) or not value):
                    self.report.error(
                        "container.reference",
                        f"Container reference {field} must be a non-empty string.",
                        location,
                    )
            if isinstance(wrapper_parent, str) and isinstance(data_parent, str) and wrapper_parent != data_parent:
                self.report.error(
                    "container.reference",
                    "Wrapper parentId and data.parentId must reference the same container.",
                    f"workflow.graph.nodes[{node_id}]",
                )
            parent = wrapper_parent if isinstance(wrapper_parent, str) and wrapper_parent else data_parent
            if isinstance(parent, str) and parent:
                parents[node_id] = parent
                if parent not in self.node_type_by_id:
                    self.report.error(
                        "container.reference",
                        f"Node {node_id!r} parentId references unknown node {parent!r}.",
                        f"workflow.graph.nodes[{node_id}].parentId",
                    )
                elif parent not in container_ids:
                    self.report.error(
                        "container.reference",
                        f"Node {node_id!r} parentId {parent!r} is not an iteration or loop.",
                        f"workflow.graph.nodes[{node_id}].parentId",
                    )
                else:
                    children_by_parent[parent].append(node_id)

            for field, container_type in (("iteration_id", "iteration"), ("loop_id", "loop")):
                ref = data.get(field)
                if ref is not None:
                    if not isinstance(ref, str) or not ref:
                        self.report.error(
                            "container.reference",
                            f"{field} must be a non-empty string.",
                            f"workflow.graph.nodes[{node_id}].data.{field}",
                        )
                    elif self.node_type_by_id.get(ref) != container_type:
                        self.report.error(
                            "container.reference",
                            f"{field} {ref!r} does not resolve to a {container_type} node.",
                            f"workflow.graph.nodes[{node_id}].data.{field}",
                        )
                flag = "isInIteration" if field == "iteration_id" else "isInLoop"
                expected_start_type = CONTAINER_START_TYPES[container_type]
                is_container_start = self.node_type_by_id.get(node_id) == expected_start_type
                if (
                    data.get(flag) is True
                    and not is_container_start
                    and (not isinstance(ref, str) or not ref)
                ):
                    self.report.error(
                        "container.reference",
                        f"{flag}: true requires a valid {field}.",
                        f"workflow.graph.nodes[{node_id}].data.{field}",
                    )

        for container_id in sorted(container_ids):
            container = self.node_by_id[container_id]
            data = _dict(container.get("data"))
            container_type = self.node_type_by_id[container_id]
            expected_start_type = CONTAINER_START_TYPES[container_type]
            start_id = data.get("start_node_id")
            if not isinstance(start_id, str) or not start_id:
                self.report.error(
                    "container.start-node",
                    f"{container_type} node requires a non-empty start_node_id.",
                    f"workflow.graph.nodes[{container_id}].data.start_node_id",
                )
            elif self.node_type_by_id.get(start_id) != expected_start_type:
                self.report.error(
                    "container.start-node",
                    f"start_node_id {start_id!r} must resolve to a {expected_start_type} node.",
                    f"workflow.graph.nodes[{container_id}].data.start_node_id",
                )
            elif parents.get(start_id) != container_id:
                self.report.error(
                    "container.start-node",
                    f"Container start node {start_id!r} must use parentId {container_id!r}.",
                    f"workflow.graph.nodes[{start_id}].parentId",
                )

            executable_children = [
                child_id
                for child_id in children_by_parent.get(container_id, [])
                if self.node_type_by_id.get(child_id) not in {"iteration-start", "loop-start"}
            ]
            if not executable_children:
                self.report.error(
                    "container.empty",
                    f"Container node {container_id!r} has no executable child nodes.",
                    f"workflow.graph.nodes[{container_id}]",
                )

        for node_id in parents:
            seen: set[str] = set()
            current = node_id
            while current in parents:
                if current in seen:
                    self.report.error(
                        "container.reference",
                        f"Container parentId chain contains a cycle at node {current!r}.",
                        f"workflow.graph.nodes[{node_id}].parentId",
                    )
                    break
                seen.add(current)
                current = parents[current]

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
            if (
                isinstance(source, str)
                and isinstance(target, str)
                and source in runtime_ids
                and target in runtime_ids
                and target not in adjacency[source]
            ):
                adjacency[source].add(target)
                indegree[target] += 1

        # Container internals are reached through their configured start helper.
        for node_id, node in self.node_by_id.items():
            data = _dict(node.get("data"))
            start_id = data.get("start_node_id")
            if (
                node_id in runtime_ids
                and isinstance(start_id, str)
                and start_id in runtime_ids
                and start_id not in adjacency[node_id]
            ):
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
        for node_id in sorted(reachable):
            node_type = self.node_type_by_id[node_id]
            node = self.node_by_id[node_id]
            data = _dict(node.get("data"))
            is_container_child = bool(node.get("parentId") or data.get("parentId"))
            if (
                not adjacency[node_id]
                and node_type not in {"end", "answer", "iteration-start", "loop-start", "loop-end"}
                and not is_container_child
            ):
                self.report.warn(
                    "graph.dead-end",
                    f"Reachable non-terminal node {node_id!r} has no outgoing edge.",
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
                elif (
                    not isinstance(variable.get("name"), str)
                    or not variable.get("name")
                    or not isinstance(variable.get("value_type"), str)
                    or not variable.get("value_type")
                ):
                    self.report.warn("workflow.variable-field", "Variable is missing name or value_type.", item_path)

    def _validate_references(self) -> None:
        seen: set[tuple[str, tuple[str, ...]]] = set()
        self._walk_references(self.workflow, "workflow", seen, allow_selector=False)

    def _walk_references(
        self,
        value: Any,
        path: str,
        seen: set[tuple[str, tuple[str, ...]]],
        *,
        allow_selector: bool,
    ) -> None:
        if isinstance(value, str):
            for match in VAR_REF_RE.finditer(value):
                selector = tuple(match.group(1).split("."))
                marker = (path, selector)
                if marker in seen:
                    continue
                seen.add(marker)
                runtime_template = ".agent_job.workflow_prompt" not in path
                self._validate_selector(selector, path, runtime_template=runtime_template)
            return
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                key_text = str(key)
                is_selector_key = (
                    key == "selector"
                    or key_text.endswith("_selector")
                    or key in {"query", "variable"}
                )
                is_variable_value = key == "value" and (
                    value.get("input_type") == "variable"
                    or value.get("value_type") == "variable"
                    or value.get("type") == "variable"
                )
                if key in SELECTOR_COLLECTION_KEYS and isinstance(child, list):
                    for index, candidate in enumerate(child):
                        if (
                            isinstance(candidate, list)
                            and len(candidate) >= 2
                            and all(isinstance(part, str) for part in candidate)
                        ):
                            selector = tuple(candidate)
                            selector_path = f"{child_path}[{index}]"
                            marker = (selector_path, selector)
                            if marker not in seen:
                                seen.add(marker)
                                self._validate_selector(selector, selector_path)
                is_plain_value_list = (
                    key == "value"
                    and isinstance(child, list)
                    and (
                        path.endswith(".option_source")
                        or path.endswith(".default")
                        or value.get("type") == "constant"
                        or "comparison_operator" in value
                    )
                )
                child_allows_selector = (
                    (allow_selector or is_selector_key or is_variable_value)
                    and not (
                        (
                            key in NON_SELECTOR_LIST_KEYS
                            or key_text.endswith("_ids")
                        )
                        and isinstance(child, list)
                    )
                    and not is_plain_value_list
                )
                if (
                    child_allows_selector
                    and isinstance(child, list)
                    and len(child) >= 2
                    and all(isinstance(part, str) for part in child)
                ):
                    selector = tuple(child)
                    marker = (child_path, selector)
                    if marker not in seen:
                        seen.add(marker)
                        self._validate_selector(selector, child_path)
                self._walk_references(
                    child,
                    child_path,
                    seen,
                    allow_selector=child_allows_selector,
                )
            return
        if isinstance(value, list):
            if allow_selector and len(value) == 2 and all(isinstance(part, str) for part in value):
                selector = tuple(value)
                marker = (path, selector)
                if marker not in seen:
                    seen.add(marker)
                    self._validate_selector(selector, path)
            for index, child in enumerate(value):
                self._walk_references(
                    child,
                    f"{path}[{index}]",
                    seen,
                    allow_selector=allow_selector,
                )

    def _validate_selector(
        self,
        selector: tuple[str, ...],
        location: str,
        *,
        runtime_template: bool = False,
    ) -> None:
        if len(selector) < 2:
            # Human Input delivery templates can contain local one-part fields
            # such as {{#url#}}; they are not workflow variable selectors.
            return
        root, output_name = selector[0], selector[1]
        if (
            runtime_template
            and root not in SYSTEM_ROOTS
            and not RUNTIME_TEMPLATE_NODE_ID_RE.fullmatch(root)
        ):
            self.report.error(
                "reference.template-node-id",
                "Template references require a 1-50 character node id containing only letters, numbers, or underscores.",
                location,
            )
        if root in SYSTEM_ROOTS:
            return
        if (
            len(selector) == 2
            and output_name.startswith("sys.")
            and self.node_type_by_id.get(root) == "start"
        ):
            # The 1.16 frontend stores Chatflow system variables as
            # [startNodeId, "sys.query"] in several node configs.
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
            if not isinstance(dependency_type, str) or dependency_type not in DEPENDENCY_TYPES:
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
            if not isinstance(node_type, str):
                continue
            candidates: list[Any] = []
            if node_type in {"llm", "question-classifier", "parameter-extractor"}:
                candidates.append(_dict(data.get("model")).get("provider"))
            elif node_type == "tool" and (
                not isinstance(data.get("provider_type"), str)
                or data.get("provider_type") not in {"workflow", "api", "mcp"}
            ):
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

    validator = Validator(document, Path(path), target_version=target_version)
    try:
        return validator.run()
    except Exception as exc:  # Defensive boundary: user YAML must never crash callers.
        validator.report.error(
            "validator.internal",
            f"Validator could not complete: {type(exc).__name__}: {exc}",
            "$",
        )
        return validator.report


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
    except (yaml.YAMLError, TypeError, ValueError) as exc:
        report.error("yaml.parse", f"YAML parse failed: {exc}", str(resolved_path))
        return report
    return validate_document(document, path=resolved_path, target_version=target_version)


# Backward-compatible library name used by early adopters of the script.
validate_file = validate_path
