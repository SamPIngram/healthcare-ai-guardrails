from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import pydicom
except Exception:  # optional import at runtime; errors handled in validate
    pydicom = None

from ..runner import ValidationResult, Severity


def _get(ds: Any, tag: str) -> Any:
    if ds is None:
        return None
    if hasattr(ds, "get"):
        try:
            return ds.get(tag)
        except Exception:
            # pydicom Dataset has attribute access too
            return getattr(ds, tag, None)
    return getattr(ds, tag, None)


@dataclass
class DICOMGenericNumericRangeCheck:
    tag: str
    name: str = "dicom_generic_numeric_range"
    unit: str = ""
    min_val: float | None = None
    max_val: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = (
        "Ensure a generic DICOM tag's numeric value is within an expected range"
    )

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        val = _get(ds, self.tag)
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message=f"Tag {self.tag} missing",
                severity=self.severity,
            )
        try:
            v = float(val)
        except (ValueError, TypeError):
            return ValidationResult(
                self.name,
                False,
                message=f"Tag {self.tag} not numeric: {val}",
                severity=self.severity,
            )

        passed = True
        msgs = []
        if self.min_val is not None:
            if self.inclusive and v < self.min_val:
                passed = False
                msgs.append(f"{v} < min {self.min_val} {self.unit}")
            if not self.inclusive and v <= self.min_val:
                passed = False
                msgs.append(f"{v} <= min {self.min_val} {self.unit}")
        if self.max_val is not None:
            if self.inclusive and v > self.max_val:
                passed = False
                msgs.append(f"{v} > max {self.max_val} {self.unit}")
            if not self.inclusive and v >= self.max_val:
                passed = False
                msgs.append(f"{v} >= max {self.max_val} {self.unit}")

        return ValidationResult(
            self.name,
            passed,
            message="; ".join(msgs),
            severity=self.severity,
            context={f"{self.tag.lower()}_{self.unit or 'value'}": v},
        )


@dataclass
class DICOMGenericValueInListCheck:
    tag: str
    allowed_values: list[Any]
    name: str = "dicom_generic_value_in_list"
    severity: Severity = Severity.WARNING
    description: str = "Ensure a generic DICOM tag's value is in the allowed list"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )

        val = _get(ds, self.tag)
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message=f"Tag {self.tag} missing",
                severity=self.severity,
            )

        passed = val in self.allowed_values
        msg = (
            ""
            if passed
            else f"Value {val!r} for tag {self.tag} not in {self.allowed_values}"
        )
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class DICOMGenericTagTypeCheck:
    tag: str
    expected_vr: str
    name: str = "dicom_generic_tag_type_check"
    severity: Severity = Severity.WARNING
    description: str = (
        "Ensure a generic DICOM tag has the expected Value Representation (VR)"
    )

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )

        try:
            element = ds[self.tag]
            actual_vr = element.VR
            passed = actual_vr == self.expected_vr
            msg = (
                ""
                if passed
                else f"Tag {self.tag} has VR {actual_vr}, expected {self.expected_vr}"
            )
            return ValidationResult(
                self.name, passed, message=msg, severity=self.severity
            )
        except KeyError:
            return ValidationResult(
                self.name,
                False,
                message=f"Tag {self.tag} not found in dataset",
                severity=self.severity,
            )
        except Exception as exc:
            return ValidationResult(
                self.name,
                False,
                message=f"Could not validate tag type: {exc}",
                severity=self.severity,
            )
