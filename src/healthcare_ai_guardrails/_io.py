from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_dicom(path: Path) -> Any:
    try:
        import pydicom

        return pydicom.dcmread(str(path))
    except Exception as exc:
        raise ValueError(f"Failed to read DICOM: {exc}") from exc


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_xml(path: Path) -> Any:
    try:
        try:
            from lxml import etree as ET  # type: ignore
        except Exception:  # pragma: no cover
            import xml.etree.ElementTree as ET  # type: ignore
        tree = ET.parse(str(path))
        return tree.getroot()
    except Exception as exc:
        raise ValueError(f"Failed to read XML: {exc}") from exc


def load_data_from_path(path: Path) -> Any:
    """Detect data format from file extension and load accordingly."""
    if path.suffix.lower() in {".dcm", ".dicom"}:
        return _read_dicom(path)
    elif path.suffix.lower() in {".json"}:
        return _read_json(path)
    elif path.suffix.lower() in {".xml"}:
        return _read_xml(path)
    else:
        text = _read_text(path)
        if text.strip().startswith("MSH"):
            return text
        try:
            return json.loads(text)
        except Exception:
            return text


def load_data_from_string(content: str) -> Any:
    """Detect data format from inline content and parse accordingly."""
    stripped = content.strip()
    if stripped.startswith("MSH"):
        return content
    if stripped.startswith("<"):
        try:
            from lxml import etree as ET  # type: ignore
        except Exception:  # pragma: no cover
            import xml.etree.ElementTree as ET  # type: ignore
        return ET.fromstring(stripped.encode())
    try:
        return json.loads(content)
    except Exception:
        return content
