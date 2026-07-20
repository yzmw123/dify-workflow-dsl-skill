"""Diagnostic models shared by the validator library and CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One stable, machine-readable validation finding."""

    severity: Severity
    code: str
    message: str
    location: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.location:
            payload["location"] = self.location
        return payload


@dataclass(slots=True)
class Report:
    """Validation result for one DSL document."""

    path: Path
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def errors(self) -> list[Diagnostic]:
        return [item for item in self.diagnostics if item.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [item for item in self.diagnostics if item.severity == "warning"]

    def error(self, code: str, message: str, location: str = "") -> None:
        self.diagnostics.append(Diagnostic("error", code, message, location))

    def warn(self, code: str, message: str, location: str = "") -> None:
        self.diagnostics.append(Diagnostic("warning", code, message, location))

    def as_dict(self) -> dict[str, object]:
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        if error_count:
            status = "invalid"
        elif warning_count:
            status = "warnings"
        else:
            status = "valid"
        return {
            "path": str(self.path),
            "status": status,
            "summary": {"errors": error_count, "warnings": warning_count},
            "diagnostics": [item.as_dict() for item in self.diagnostics],
        }

    def format_text(self) -> str:
        lines = [f"== {self.path}"]
        for item in self.diagnostics:
            label = "ERROR" if item.severity == "error" else "WARN"
            location = f" {item.location}:" if item.location else ":"
            lines.append(f"{label} [{item.code}]{location} {item.message}")
        if not self.diagnostics:
            lines.append("OK")
        else:
            lines.append(f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return "\n".join(lines)
