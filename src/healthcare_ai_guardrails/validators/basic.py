from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from ..runner import ValidationResult, Severity


@dataclass
class RangeCheck:
    """Numerical range check on a path in a dict-like structure.

    If `path` is None, `value_selector` must be provided and is called with data.
    """

    name: str
    path: Sequence[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = ""
    value_selector: callable | None = None

    def _extract(self, data: Any) -> Any:
        if self.value_selector is not None:
            return self.value_selector(data)
        if self.path is None:
            raise ValueError("Either path or value_selector must be provided")
        cur: Any = data
        for key in self.path:
            if isinstance(cur, dict):
                cur = cur.get(key)
            else:
                cur = getattr(cur, key, None)
        return cur

    def validate(self, data: Any) -> ValidationResult:
        value = self._extract(data)
        passed = True
        msgs = []
        if value is None:
            return ValidationResult(
                self.name, False, message="Value missing", severity=self.severity
            )
        try:
            num = float(value)
        except Exception:
            return ValidationResult(
                self.name,
                False,
                message=f"Value not numeric: {value}",
                severity=self.severity,
            )
        if self.min_value is not None:
            if self.inclusive and num < self.min_value:
                passed = False
                msgs.append(f"{num} < min {self.min_value}")
            if not self.inclusive and num <= self.min_value:
                passed = False
                msgs.append(f"{num} <= min {self.min_value}")
        if self.max_value is not None:
            if self.inclusive and num > self.max_value:
                passed = False
                msgs.append(f"{num} > max {self.max_value}")
            if not self.inclusive and num >= self.max_value:
                passed = False
                msgs.append(f"{num} >= max {self.max_value}")
        return ValidationResult(self.name, passed, message="; ".join(msgs))


@dataclass
class ChoiceCheck:
    name: str
    path: Sequence[str] | None = None
    allowed: Iterable[Any] = ()
    case_insensitive: bool = False
    severity: Severity = Severity.WARNING
    description: str = ""
    value_selector: callable | None = None

    def _extract(self, data: Any) -> Any:
        if self.value_selector is not None:
            return self.value_selector(data)
        if self.path is None:
            raise ValueError("Either path or value_selector must be provided")
        cur: Any = data
        for key in self.path:
            if isinstance(cur, dict):
                cur = cur.get(key)
            else:
                cur = getattr(cur, key, None)
        return cur

    def validate(self, data: Any) -> ValidationResult:
        value = self._extract(data)
        if value is None:
            return ValidationResult(
                self.name, False, message="Value missing", severity=self.severity
            )
        allowed = list(self.allowed)
        if self.case_insensitive and isinstance(value, str):
            allowed = [str(a).lower() for a in allowed]
            value_cmp = value.lower()
        else:
            value_cmp = value
        passed = value_cmp in allowed
        msg = "" if passed else f"{value!r} not in allowed set: {allowed}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class RequiredFieldsCheck:
    name: str
    paths: list[Sequence[str]]
    severity: Severity = Severity.ERROR
    description: str = ""

    def _extract(self, data: Any, path: Sequence[str]) -> Any:
        cur: Any = data
        for key in path:
            if isinstance(cur, dict):
                cur = cur.get(key)
            else:
                cur = getattr(cur, key, None)
        return cur

    def validate(self, data: Any) -> ValidationResult:
        missing = []
        for p in self.paths:
            if self._extract(data, p) in (None, ""):
                missing.append(".".join(p))
        passed = len(missing) == 0
        msg = "" if passed else f"Missing required fields: {missing}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)
