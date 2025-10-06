from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional

from ..runner import ValidationResult, Severity

try:
    from lxml import etree as ET  # better XPath support if available
except Exception:  # pragma: no cover - fallback
    import xml.etree.ElementTree as ET  # type: ignore


def _as_root(xml: Any) -> Optional[Any]:
    if xml is None:
        return None
    if hasattr(xml, "getroot"):
        try:
            return xml.getroot()
        except Exception:
            return None
    # If a string is passed, try to parse
    if isinstance(xml, str):
        try:
            return ET.fromstring(xml)
        except Exception:
            return None
    # Might already be an Element
    return xml


@dataclass
class HL7v3XPathExistsCheck:
    xpath: str
    namespaces: Dict[str, str] | None = None
    name: str = "hl7v3_xpath_exists"
    severity: Severity = Severity.WARNING
    description: str = "Ensure an XPath resolves to at least one node/value"

    def validate(self, xml: Any) -> ValidationResult:
        root = _as_root(xml)
        if root is None:
            return ValidationResult(
                self.name, False, message="No XML to validate", severity=self.severity
            )
        try:
            if hasattr(root, "xpath"):
                result = root.xpath(self.xpath, namespaces=self.namespaces or {})
            else:
                tree = ET.ElementTree(root)
                result = tree.findall(self.xpath, namespaces=self.namespaces or {})
            passed = bool(result)
            return ValidationResult(
                self.name,
                passed,
                message="" if passed else f"No match for {self.xpath}",
                severity=self.severity,
            )
        except Exception as exc:
            return ValidationResult(
                self.name, False, message=f"XPath error: {exc}", severity=self.severity
            )


@dataclass
class HL7v3XPathValueInListCheck:
    xpath: str
    allowed: List[str]
    namespaces: Dict[str, str] | None = None
    case_insensitive: bool = False
    attr: str | None = None
    name: str = "hl7v3_xpath_value_in_list"
    severity: Severity = Severity.WARNING
    description: str = (
        "Ensure the XPath-selected value (attribute or text) is in allowed list"
    )

    def validate(self, xml: Any) -> ValidationResult:
        root = _as_root(xml)
        if root is None:
            return ValidationResult(
                self.name, False, message="No XML to validate", severity=self.severity
            )
        try:
            if hasattr(root, "xpath"):
                result = root.xpath(self.xpath, namespaces=self.namespaces or {})
            else:
                tree = ET.ElementTree(root)
                result = tree.findall(self.xpath, namespaces=self.namespaces or {})
            val = None
            if result:
                node = result[0]
                if isinstance(node, str):
                    val = node
                elif hasattr(node, "get"):
                    # prefer explicit attribute if provided
                    if self.attr:
                        val = node.get(self.attr)
                    # fall back to common HL7v3 attribute 'value', else element text
                    if val is None:
                        val = node.get("value")
                    if val is None:
                        val = node.text or ""
                else:
                    val = str(node)
            if val is None:
                return ValidationResult(
                    self.name,
                    False,
                    message=f"No value at {self.xpath}",
                    severity=self.severity,
                )
            cmp_val = val.lower() if self.case_insensitive else val
            allowed = (
                [a.lower() for a in self.allowed]
                if self.case_insensitive
                else self.allowed
            )
            passed = cmp_val in allowed
            return ValidationResult(
                self.name,
                passed,
                message="" if passed else f"{val!r} not in {self.allowed}",
                severity=self.severity,
            )
        except Exception as exc:
            return ValidationResult(
                self.name, False, message=f"XPath error: {exc}", severity=self.severity
            )


@dataclass
class HL7v3XPathRegexMatchCheck:
    xpath: str
    pattern: str
    namespaces: Dict[str, str] | None = None
    attr: str | None = None
    name: str = "hl7v3_xpath_regex_match"
    severity: Severity = Severity.WARNING
    description: str = (
        "Ensure the XPath-selected value (attribute or text) matches a regex"
    )

    def validate(self, xml: Any) -> ValidationResult:
        root = _as_root(xml)
        if root is None:
            return ValidationResult(
                self.name, False, message="No XML to validate", severity=self.severity
            )
        try:
            if hasattr(root, "xpath"):
                result = root.xpath(self.xpath, namespaces=self.namespaces or {})
            else:
                tree = ET.ElementTree(root)
                result = tree.findall(self.xpath, namespaces=self.namespaces or {})
            val = None
            if result:
                node = result[0]
                if isinstance(node, str):
                    val = node
                elif hasattr(node, "get"):
                    if self.attr:
                        val = node.get(self.attr)
                    if val is None:
                        val = node.get("value")
                    if val is None:
                        val = node.text or ""
                else:
                    val = str(node)
            if val is None:
                return ValidationResult(
                    self.name,
                    False,
                    message=f"No value at {self.xpath}",
                    severity=self.severity,
                )
            passed = re.fullmatch(self.pattern, val) is not None
            return ValidationResult(
                self.name,
                passed,
                message="" if passed else f"{val!r} does not match {self.pattern}",
                severity=self.severity,
            )
        except Exception as exc:
            return ValidationResult(
                self.name, False, message=f"XPath error: {exc}", severity=self.severity
            )


@dataclass
class HL7v3XPathNumericRangeCheck:
    xpath: str
    min_value: float | None = None
    max_value: float | None = None
    inclusive: bool = True
    namespaces: Dict[str, str] | None = None
    attr: str | None = None
    name: str = "hl7v3_xpath_numeric_range"
    severity: Severity = Severity.WARNING
    description: str = (
        "Ensure the XPath-selected value (attribute or text) is numeric and within range"
    )

    def validate(self, xml: Any) -> ValidationResult:
        root = _as_root(xml)
        if root is None:
            return ValidationResult(
                self.name, False, message="No XML to validate", severity=self.severity
            )
        try:
            if hasattr(root, "xpath"):
                result = root.xpath(self.xpath, namespaces=self.namespaces or {})
            else:
                tree = ET.ElementTree(root)
                result = tree.findall(self.xpath, namespaces=self.namespaces or {})
            val = None
            if result:
                node = result[0]
                if isinstance(node, str):
                    val = node
                elif hasattr(node, "get"):
                    if self.attr:
                        val = node.get(self.attr)
                    if val is None:
                        val = node.get("value")
                    if val is None:
                        val = node.text or ""
                else:
                    val = str(node)
            if val is None:
                return ValidationResult(
                    self.name,
                    False,
                    message=f"No value at {self.xpath}",
                    severity=self.severity,
                )
            try:
                v = float(val)
            except (TypeError, ValueError):
                return ValidationResult(
                    self.name,
                    False,
                    message=f"Not numeric: {val!r}",
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
                self.name, passed, message="; ".join(msgs), severity=self.severity
            )
        except Exception as exc:
            return ValidationResult(
                self.name, False, message=f"XPath error: {exc}", severity=self.severity
            )
