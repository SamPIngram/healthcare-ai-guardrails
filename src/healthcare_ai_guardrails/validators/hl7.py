from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Tuple

from ..runner import ValidationResult, Severity


def _split_lines(message: str) -> List[str]:
    # HL7 v2 segments are delimited by carriage return (\r); some files use \n
    message = message.replace("\r\n", "\n").replace("\r", "\n")
    return [line for line in message.split("\n") if line.strip()]


def _detect_separators(lines: List[str]) -> Tuple[str, str, str, str]:
    # Returns (field_sep, comp_sep, rep_sep, subcomp_sep)
    # Defaults per HL7: | ^ ~ &
    field_sep, comp_sep, rep_sep, subcomp_sep = "|", "^", "~", "&"
    if lines and lines[0].startswith("MSH"):
        msh = lines[0]
        if len(msh) > 3:
            field_sep = msh[3]
        parts = msh.split(field_sep)
        # MSH-2 Encoding Characters defines component ^ repetition ~ escape \\ subcomponent &
        # After splitting, parts[0] == 'MSH', parts[1] == MSH-2 (encoding characters)
        if len(parts) > 1 and parts[1]:
            enc = parts[1]
            if len(enc) >= 1:
                comp_sep = enc[0]
            if len(enc) >= 2:
                rep_sep = enc[1]
            # enc[2] is escape; unused here
            if len(enc) >= 4:
                subcomp_sep = enc[3]
    return field_sep, comp_sep, rep_sep, subcomp_sep


def _get_field_value(message: str, path: str) -> str | None:
    """
    Resolve an HL7 v2 value by path like "PID-5.1" (Segment-FIELD[rep].COMP.SUB).
    - Segment: 3-letter code
    - FIELD: 1-based index (for MSH, note MSH-1 is the field separator itself)
    - Optional repetition index: [n] 1-based; defaults to first repetition
    - Optional .COMP (1-based)
    - Optional .SUB (1-based)
    Simplifications: uses first segment occurrence; ignores escape sequences.
    """
    if not isinstance(message, str):
        return None
    lines = _split_lines(message)
    if not lines:
        return None
    field_sep, comp_sep, rep_sep, subcomp_sep = _detect_separators(lines)

    seg_part, *rest = path.split("-")
    if not rest:
        return None
    seg = seg_part.strip().upper()
    field_part = rest[0]

    # Handle repetitions: FIELD[rep]
    rep_index = 1
    m = re.match(r"^(\d+)(?:\[(\d+)\])?", field_part)
    if not m:
        return None
    field_index = int(m.group(1))
    if m.group(2):
        rep_index = int(m.group(2))

    comp_index = None
    subcomp_index = None
    # Handle .COMP and .SUB (optional)
    if "." in field_part:
        # e.g., 5.1 or 5.1.2
        after = field_part.split(".", 1)[1]
        parts = after.split(".")
        if parts and parts[0].isdigit():
            comp_index = int(parts[0])
        if len(parts) > 1 and parts[1].isdigit():
            subcomp_index = int(parts[1])

    # Find first occurrence of the segment
    seg_line = None
    for line in lines:
        if line.startswith(seg + field_sep):
            seg_line = line
            break
    if seg_line is None:
        return None

    fields = seg_line.split(field_sep)
    # For non-MSH segments, fields[0] is segment name, field 1 is fields[1]
    # For MSH, MSH-1 is the field separator character (not present in split fields)
    if seg == "MSH":
        if field_index == 1:
            field_val = field_sep
        else:
            target_idx = field_index - 1  # MSH-2 -> fields[1], MSH-3 -> fields[2], ...
            if target_idx >= len(fields):
                return None
            field_val = fields[target_idx]
    else:
        target_idx = field_index  # PID-1 -> fields[1]
        if target_idx >= len(fields):
            return None
        field_val = fields[target_idx]
    if field_val is None or field_val == "":
        return None

    # Repetitions
    reps = field_val.split(rep_sep) if rep_sep in field_val else [field_val]
    if rep_index < 1 or rep_index > len(reps):
        return None
    rep_val = reps[rep_index - 1]

    # Components
    if comp_index is not None:
        comps = rep_val.split(comp_sep)
        if comp_index < 1 or comp_index > len(comps):
            return None
        comp_val = comps[comp_index - 1]
    else:
        comp_val = rep_val

    # Subcomponents
    if subcomp_index is not None:
        subs = comp_val.split(subcomp_sep)
        if subcomp_index < 1 or subcomp_index > len(subs):
            return None
        return subs[subcomp_index - 1]

    return comp_val


@dataclass
class HL7FieldExistsCheck:
    path: str
    name: str = "hl7_field_exists"
    severity: Severity = Severity.WARNING
    description: str = "Ensure the HL7 v2 path resolves to a non-empty value"

    def validate(self, message: Any) -> ValidationResult:
        val = _get_field_value(message, self.path)
        passed = val is not None and str(val) != ""
        msg = "" if passed else f"Path {self.path} missing or empty"
        ctx: Dict[str, Any] = {"path": self.path}
        if val is not None:
            ctx["value"] = val
        return ValidationResult(
            self.name, passed, message=msg, severity=self.severity, context=ctx
        )


@dataclass
class HL7ValueInListCheck:
    path: str
    allowed: List[str]
    case_insensitive: bool = False
    name: str = "hl7_value_in_list"
    severity: Severity = Severity.WARNING
    description: str = "Ensure the HL7 v2 value is in the allowed list"

    def validate(self, message: Any) -> ValidationResult:
        val = _get_field_value(message, self.path)
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message=f"Path {self.path} missing",
                severity=self.severity,
            )
        sval = str(val)
        allowed = self.allowed
        if self.case_insensitive:
            allowed = [a.lower() for a in allowed]
            sval_cmp = sval.lower()
        else:
            sval_cmp = sval
        passed = sval_cmp in allowed
        msg = "" if passed else f"Value {sval!r} not in {self.allowed} for {self.path}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class HL7RegexMatchCheck:
    path: str
    pattern: str
    name: str = "hl7_regex_match"
    severity: Severity = Severity.WARNING
    description: str = "Ensure the HL7 v2 value matches a regex"

    def validate(self, message: Any) -> ValidationResult:
        val = _get_field_value(message, self.path)
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message=f"Path {self.path} missing",
                severity=self.severity,
            )
        sval = str(val)
        passed = re.fullmatch(self.pattern, sval) is not None
        msg = (
            ""
            if passed
            else f"Value {sval!r} does not match {self.pattern} for {self.path}"
        )
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class HL7NumericRangeCheck:
    path: str
    min_value: float | None = None
    max_value: float | None = None
    inclusive: bool = True
    name: str = "hl7_numeric_range"
    severity: Severity = Severity.WARNING
    description: str = "Ensure the HL7 v2 numeric value is within range"

    def validate(self, message: Any) -> ValidationResult:
        val = _get_field_value(message, self.path)
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message=f"Path {self.path} missing",
                severity=self.severity,
            )
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ValidationResult(
                self.name,
                False,
                message=f"Value {val!r} not numeric for {self.path}",
                severity=self.severity,
            )

        passed = True
        msgs: List[str] = []
        if self.min_value is not None:
            if self.inclusive and v < self.min_value:
                passed = False
                msgs.append(f"{v} < min {self.min_value}")
            if not self.inclusive and v <= self.min_value:
                passed = False
                msgs.append(f"{v} <= min {self.min_value}")
        if self.max_value is not None:
            if self.inclusive and v > self.max_value:
                passed = False
                msgs.append(f"{v} > max {self.max_value}")
            if not self.inclusive and v >= self.max_value:
                passed = False
                msgs.append(f"{v} >= max {self.max_value}")

        return ValidationResult(
            self.name,
            passed,
            message="; ".join(msgs),
            severity=self.severity,
            context={"value": v},
        )
