"""Dify 1.18 additions, checked against the 1.18.0 tagged models.

These checks do not resolve workspace resources or replace Dify's import gate.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .models import Report


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _extra(value: dict, allowed: set[str], report: Report, code: str, path: str) -> None:
    for key in value:
        if key not in allowed:
            report.error(code, f"Unknown Dify 1.18 field {key!r}.", f"{path}.{key}")


def validate_workspace_skills(value: Any, report: Report, path: str) -> None:
    code = "agent.workspace-skills"
    if not isinstance(value, list):
        report.error(code, "workspace_skills must be a list.", path)
        return
    for i, item in enumerate(value):
        loc = f"{path}[{i}]"
        if not isinstance(item, dict):
            report.error(code, "Skill binding must be a mapping.", loc)
            continue
        _extra(item, {"name", "display_name", "description", "priority"}, report, code, loc)
        name = item.get("name")
        if not isinstance(name, str) or not 1 <= len(name) <= 64:
            report.error(code, "Skill name must contain 1-64 characters.", f"{loc}.name")
        for key in ("display_name", "description"):
            if not isinstance(item.get(key, ""), str):
                report.error(code, f"{key} must be a string.", f"{loc}.{key}")
        priority = item.get("priority")
        if type(priority) is not int or priority < 0:
            report.error(code, "priority is required and must be a non-negative integer.", f"{loc}.priority")


def validate_spaces(knowledge: dict, report: Report, path: str) -> None:
    value = knowledge.get("spaces", [])
    code = "agent.knowledge-spaces"
    loc = f"{path}.spaces"
    if not isinstance(value, list):
        report.error(code, "knowledge.spaces must be a list.", loc)
        return
    if len(value) > 10:
        report.error(code, "At most 10 knowledge spaces are allowed.", loc)
    identities: dict[str, list[str]] = {"id": [], "name": [], "control_space_id": []}
    normalized_items = []
    for i, item in enumerate(value):
        item_loc = f"{loc}[{i}]"
        if not isinstance(item, dict):
            report.error(code, "Knowledge space must be a mapping.", item_loc)
            continue
        _extra(item, {"id", "name", "control_space_id", "description", "is_missing"}, report, code, item_loc)
        normalized = {}
        for key, limit in (("id", 255), ("name", 120)):
            field = item.get(key)
            if (not isinstance(field, str) or not 1 <= len(field) <= limit or not field.strip()
                    or any(ord(c) < 32 or ord(c) == 127 for c in field.strip())):
                report.error(code, f"{key} must contain 1-{limit} characters without control characters.", f"{item_loc}.{key}")
            else:
                normalized[key] = field.strip().casefold()
                identities[key].append(normalized[key])
        field = item.get("control_space_id")
        try:
            if not isinstance(field, str) or len(field) != 36:
                raise ValueError
            identities["control_space_id"].append(str(UUID(field)))
        except ValueError:
            report.error(code, "control_space_id must be a 36-character UUID from the target workspace.", f"{item_loc}.control_space_id")
        description = item.get("description")
        if description is not None and (not isinstance(description, str) or len(description) > 2000):
            report.error(code, "description must be a string of at most 2000 characters or null.", item_loc)
        if not isinstance(item.get("is_missing", False), bool):
            report.error(code, "is_missing must be boolean.", f"{item_loc}.is_missing")
        normalized_items.append(normalized)
    for key, values in identities.items():
        if len(values) != len(set(values)):
            report.error(code, f"Knowledge space {key} values must be unique ignoring case.", loc)
    by_id = {item["id"]: item for item in normalized_items if "id" in item}
    for item in normalized_items:
        if item.get("name") in by_id and by_id[item["name"]] is not item:
            report.error(code, "A knowledge alias must not shadow another binding ID.", loc)
    for key in ("id", "name"):
        classic = {item[key].strip().casefold() for item in _list(knowledge.get("sets"))
                   if isinstance(item, dict) and isinstance(item.get(key), str)}
        if classic.intersection(identities[key]):
            report.error(code, f"Knowledge {key} values must be unique across spaces and classic sets.", loc)


def _routes(value: Any, report: Report, path: str) -> None:
    code = "node.agent-v2.routes"
    if not isinstance(value, dict):
        report.error(code, "Output routes must be a mapping.", path)
        return
    _extra(value, {"enabled", "routes"}, report, code, path)
    enabled = value.get("enabled", False)
    if not isinstance(enabled, bool):
        report.error(code, "enabled must be boolean.", f"{path}.enabled")
    routes = value.get("routes", [])
    if not isinstance(routes, list):
        report.error(code, "routes must be a list.", f"{path}.routes")
        return
    if enabled is True and len(routes) < 2:
        report.error(code, "Enabled output routes require at least two routes.", path)
    ids = []
    for i, route in enumerate(routes):
        loc = f"{path}.routes[{i}]"
        if not isinstance(route, dict):
            report.error(code, "Each route must be a mapping.", loc)
            continue
        _extra(route, {"id", "name", "label"}, report, code, loc)
        route_id = route.get("id")
        if not isinstance(route_id, str) or not route_id.strip() or route_id in {"source", "target", "fail-branch"}:
            report.error(code, "Route ID must be nonblank and must not use a system handle.", f"{loc}.id")
        else:
            ids.append(route_id)
        name = route.get("name", "")
        if not isinstance(name, str) or (enabled is True and not name.strip()):
            report.error(code, "Enabled routes require a nonblank selection condition in name.", f"{loc}.name")
        if route.get("label") is not None and not isinstance(route["label"], str):
            report.error(code, "Route label must be a string or null.", f"{loc}.label")
    if len(ids) != len(set(ids)):
        report.error(code, "Route IDs must be unique.", path)


def route_handles(data: dict) -> set[str] | None:
    routes = _mapping(_mapping(data.get("agent_job")).get("output_routes"))
    if routes.get("enabled") is not True:
        return None
    return {item["id"] for item in _list(routes.get("routes"))
            if isinstance(item, dict) and isinstance(item.get("id"), str)}


def validate_routes(data: dict, job: dict, report: Report, path: str) -> None:
    job_routes = job.get("output_routes", {})
    _routes(job_routes, report, f"{path}.agent_job.output_routes")
    if "agent_output_routes" in data:
        canvas_routes = data["agent_output_routes"]
        _routes(canvas_routes, report, f"{path}.agent_output_routes")
        # Both representations drive execution: graph branching and bound job selection.
        def normalized(value: Any) -> tuple:
            obj = _mapping(value)
            return (obj.get("enabled", False), [
                (r.get("id"), r.get("name", ""), r.get("label")) if isinstance(r, dict) else r
                for r in _list(obj.get("routes"))])
        if normalized(canvas_routes) != normalized(job_routes):
            report.error("node.agent-v2.routes-mismatch", "agent_output_routes must match agent_job.output_routes.", path)
    elif _mapping(job_routes).get("enabled") is True:
        report.error("node.agent-v2.routes-mismatch", "Routed portable nodes also require matching agent_output_routes.", path)
    if _mapping(job_routes).get("enabled") is True and data.get("error_strategy") == "default-value":
        report.error("node.agent-v2.routes-error-strategy", "Output routes cannot use node-level default-value handling.", path)
    if "agent_task" in data and not isinstance(data["agent_task"], str):
        report.error("node.agent-v2.task", "agent_task must be a string.", f"{path}.agent_task")


def validate_retrieval(data: dict, report: Report, path: str) -> None:
    code = "node.knowledge-v2.config"
    spaces = data.get("control_space_ids")
    if (not isinstance(spaces, list) or not 1 <= len(spaces) <= 10
            or any(not isinstance(s, str) or not s.strip() or len(s) > 1000 for s in spaces)):
        report.error(code, "control_space_ids must contain 1-10 nonblank workspace IDs.", path)
    selectors = []
    for key in ("query_variable_selector", "query_attachment_selector"):
        value = data.get(key)
        if value not in (None, []):
            selectors.append(value)
            if (not isinstance(value, list) or not 2 <= len(value) <= 10
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 255 for v in value)):
                report.error(code, f"{key} must have 2-10 nonblank string parts.", f"{path}.{key}")
    if not selectors:
        report.error(code, "Provide a query text or query attachment selector.", path)
    if data.get("mode") not in (None, "deep", "fast", "research"):
        report.error(code, "mode must be deep, fast, research, or null.", path)
    top_n = data.get("top_n", 10)
    if type(top_n) is not int or not 1 <= top_n <= 100:
        report.error(code, "top_n must be an integer from 1 to 100.", path)
    score = data.get("score_threshold")
    if score is not None and (type(score) not in (int, float) or not 0 <= score <= 1):
        report.error(code, "score_threshold must be from 0 to 1 or null.", path)
    if data.get("metadata_filtering_mode", "disabled") not in ("disabled", "automatic", "manual"):
        report.error(code, "Invalid metadata_filtering_mode.", path)
    for key in ("reranking_model", "metadata_model_config", "metadata_filtering_conditions", "metadata_filters"):
        if data.get(key) is not None and not isinstance(data[key], dict):
            report.error(code, f"{key} must be a mapping or null.", f"{path}.{key}")


def validate_site(value: Any, report: Report) -> None:
    if value is None:
        return
    code = "site.config"
    if not isinstance(value, dict):
        report.error(code, "site must be a mapping or null.", "site")
        return
    booleans = {"chat_color_theme_inverted", "show_workflow_steps", "use_icon_as_answer_icon"}
    strings = {"title", "description", "icon_type", "icon", "icon_background", "default_language",
               "chat_color_theme", "copyright", "privacy_policy", "input_placeholder", "custom_disclaimer"}
    required = booleans | {"title", "default_language", "custom_disclaimer"}
    _extra(value, booleans | strings, report, code, "site")
    for key, field in value.items():
        if field is None and key not in required:
            continue
        if key in booleans and not isinstance(field, bool):
            report.error(code, f"{key} must be boolean.", f"site.{key}")
        if key in strings and not isinstance(field, str):
            report.error(code, f"{key} must be a string.", f"site.{key}")
    for key, limit in (("title", 255), ("default_language", 255), ("custom_disclaimer", 512)):
        field = value.get(key)
        if isinstance(field, str) and (len(field) > limit or (key == "default_language" and not field)):
            report.error(code, f"Invalid {key} length (maximum {limit}).", f"site.{key}")
    if value.get("icon_type") not in (None, "emoji", "image", "link"):
        report.error(code, "Invalid Site icon_type.", "site.icon_type")
