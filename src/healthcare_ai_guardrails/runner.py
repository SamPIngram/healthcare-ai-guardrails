from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Protocol, runtime_checkable


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    name: str
    passed: bool
    message: str = ""
    severity: Severity = Severity.WARNING
    context: Dict[str, Any] | None = None


@runtime_checkable
class Validator(Protocol):
    name: str
    description: str
    severity: Severity

    def validate(self, data: Any) -> ValidationResult: ...


class GuardrailRunner:
    """Executes a set of validators on given data.

    - For input data, pass the preprocessed payload (dict, pydicom.Dataset, etc.)
    - For output data, pass your model's output structure.
    """

    def __init__(self, validators: Iterable[Validator]):
        self.validators: List[Validator] = list(validators)

    def run(self, data: Any) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for v in self.validators:
            try:
                result = v.validate(data)
            except Exception as exc:  # guardrails should not crash pipelines
                result = ValidationResult(
                    name=getattr(v, "name", v.__class__.__name__),
                    passed=False,
                    message=f"Validator raised exception: {exc}",
                    severity=getattr(v, "severity", Severity.ERROR),
                    context={"exception": repr(exc)},
                )
            results.append(result)
        return results
