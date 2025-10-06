from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import load_spec
from .runner import GuardrailRunner


def _read_dicom(path: Path) -> Any:
    try:
        import pydicom

        return pydicom.dcmread(str(path))
    except Exception as exc:
        raise SystemExit(f"Failed to read DICOM: {exc}")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_xml(path: Path) -> Any:
    try:
        # Prefer lxml if available
        try:
            from lxml import etree as ET  # type: ignore
        except Exception:  # pragma: no cover
            import xml.etree.ElementTree as ET  # type: ignore
        tree = ET.parse(str(path))
        # For lxml, pass the root Element (supports rich xpath); for stdlib, ElementTree works with .findall
        return tree.getroot()
    except Exception as exc:
        raise SystemExit(f"Failed to read XML: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Healthcare AI Guardrails")
    parser.add_argument("spec", type=str, help="Path to YAML spec file")
    parser.add_argument(
        "data", type=str, help="Path to input/output data (DICOM .dcm or JSON)"
    )
    parser.add_argument(
        "--mode", choices=["input", "output"], default="input", help="Which set to run"
    )
    args = parser.parse_args(argv)

    spec = load_spec(args.spec)
    data_path = Path(args.data)
    if data_path.suffix.lower() in {".dcm", ".dicom"}:
        data = _read_dicom(data_path)
    elif data_path.suffix.lower() in {".json"}:
        data = _read_json(data_path)
    elif data_path.suffix.lower() in {".xml"}:
        data = _read_xml(data_path)
    else:
        # Try HL7 v2 text files (.hl7 or no extension) or fall back to raw text
        text = _read_text(data_path)
        if text.strip().startswith("MSH"):
            data = text  # HL7 v2 message string
        else:
            # Fallback: attempt JSON parse, else keep as raw text
            try:
                data = json.loads(text)
            except Exception:
                data = text

    validators = (
        spec.input_validators if args.mode == "input" else spec.output_validators
    )
    runner = GuardrailRunner(validators)
    results = runner.run(data)

    any_fail = False
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if not r.passed:
            any_fail = True
        msg = f" - {r.message}" if r.message else ""
        print(f"[{status}] ({r.severity}) {r.name}{msg}")

    return 1 if any_fail else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
