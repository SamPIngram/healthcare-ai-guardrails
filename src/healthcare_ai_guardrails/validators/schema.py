from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from ..runner import ValidationResult, Severity


@dataclass
class JSONSchemaCheck:
    name: str = "json_schema_check"
    schema: Dict[str, Any] | None = None
    severity: Severity = Severity.ERROR
    description: str = "Validate structure using a JSON Schema"

    def validate(self, data: Any) -> ValidationResult:
        try:
            import jsonschema
        except Exception:
            return ValidationResult(
                self.name,
                False,
                message="jsonschema not installed",
                severity=Severity.ERROR,
            )
        if not self.schema:
            return ValidationResult(
                self.name, False, message="No schema provided", severity=self.severity
            )
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            return ValidationResult(self.name, True, message="")
        except jsonschema.ValidationError as e:
            return ValidationResult(
                self.name,
                False,
                message=f"Schema validation error: {e.message}",
                severity=self.severity,
                context={"path": list(e.path), "validator": e.validator},
            )
        except Exception as exc:
            return ValidationResult(
                self.name,
                False,
                message=f"Schema validation failed: {exc}",
                severity=self.severity,
            )
