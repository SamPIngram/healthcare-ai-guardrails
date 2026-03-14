"""MCP server exposing the healthcare-ai-guardrails QA pipeline as tools.

Run with:
    hc-guardrails-mcp
    # or
    python -m healthcare_ai_guardrails.mcp_server

Configure in Claude Desktop / MCP Inspector as a stdio server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from mcp.server.fastmcp import FastMCP

from ._io import load_data_from_path, load_data_from_string
from .config import load_spec, load_spec_from_string
from .runner import GuardrailRunner

mcp = FastMCP("healthcare-ai-guardrails")

# ---------------------------------------------------------------------------
# Validator type catalog (used by list_validator_types)
# ---------------------------------------------------------------------------

_VALIDATOR_CATALOG: List[Dict[str, Any]] = [
    # Generic
    {
        "category": "generic",
        "type": "range",
        "description": "Checks that a numeric field at a given JSON path falls within [min, max].",
        "required_params": ["path"],
        "optional_params": [
            "min",
            "max",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "generic",
        "type": "choice",
        "description": "Checks that a field at a given JSON path is one of the allowed values.",
        "required_params": ["path", "allowed"],
        "optional_params": ["case_insensitive", "name", "severity", "description"],
    },
    {
        "category": "generic",
        "type": "required_fields",
        "description": "Checks that a set of JSON paths are all present and non-null.",
        "required_params": ["paths"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "generic",
        "type": "json_schema",
        "description": "Validates data against a JSON Schema (Draft 2020-12).",
        "required_params": ["schema"],
        "optional_params": ["name", "severity", "description"],
    },
    # DICOM
    {
        "category": "dicom",
        "type": "dicom_patient_age",
        "description": "Checks patient age is within a year range. Parses age strings (e.g. '045Y', '008M') and birthdate fallback.",
        "required_params": [],
        "optional_params": [
            "min_years",
            "max_years",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "dicom",
        "type": "dicom_modality",
        "description": "Checks that the DICOM Modality tag is in the allowed list (e.g. CT, MR, US).",
        "required_params": ["allowed"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_patient_sex",
        "description": "Checks that PatientSex is in the allowed list (default: M, F, O).",
        "required_params": [],
        "optional_params": ["allowed", "name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_patient_position",
        "description": "Checks that PatientPosition is in the allowed list (e.g. HFS, FFP).",
        "required_params": ["allowed"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_slice_thickness",
        "description": "Checks that SliceThickness (mm) is within [min_mm, max_mm].",
        "required_params": [],
        "optional_params": [
            "min_mm",
            "max_mm",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "dicom",
        "type": "dicom_pixel_spacing",
        "description": "Checks that both PixelSpacing values (mm) are within [min_mm, max_mm].",
        "required_params": [],
        "optional_params": [
            "min_mm",
            "max_mm",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "dicom",
        "type": "dicom_image_orientation",
        "description": "Checks that ImageOrientationPatient vectors are orthogonal (dot product near zero).",
        "required_params": [],
        "optional_params": ["tolerance", "name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_sop_class",
        "description": "Checks that the SOPClassUID is in the allowed list of UIDs.",
        "required_params": ["allowed"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_body_part_examined",
        "description": "Checks that BodyPartExamined is in the allowed list.",
        "required_params": ["allowed"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_photometric_interpretation",
        "description": "Checks that PhotometricInterpretation is in the allowed list (e.g. MONOCHROME2, RGB).",
        "required_params": ["allowed"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_pixel_intensity_range",
        "description": "Checks that all pixel intensity values fall within [min, max].",
        "required_params": [],
        "optional_params": [
            "min",
            "max",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "dicom",
        "type": "dicom_protocol_name",
        "description": "Checks that ProtocolName is in the allowed list.",
        "required_params": ["allowed"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_rt_structure",
        "description": "Checks that required ROI names are present in an RT Structure Set.",
        "required_params": ["required_rois"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom",
        "type": "dicom_kvp",
        "description": "Checks that X-ray tube voltage KVP is within [min_kvp, max_kvp].",
        "required_params": [],
        "optional_params": [
            "min_kvp",
            "max_kvp",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "dicom",
        "type": "dicom_tube_current",
        "description": "Checks that X-ray tube current (mA) is within [min_ma, max_ma].",
        "required_params": [],
        "optional_params": [
            "min_ma",
            "max_ma",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "dicom",
        "type": "dicom_exposure_time",
        "description": "Checks that X-ray exposure time (ms) is within [min_ms, max_ms].",
        "required_params": [],
        "optional_params": [
            "min_ms",
            "max_ms",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    # DICOM generic
    {
        "category": "dicom_generic",
        "type": "dicom_generic_numeric_range",
        "description": "Generic numeric range check on any DICOM tag by name.",
        "required_params": ["tag"],
        "optional_params": [
            "unit",
            "min_val",
            "max_val",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "dicom_generic",
        "type": "dicom_generic_value_in_list",
        "description": "Generic value-in-list check on any DICOM tag by name.",
        "required_params": ["tag", "allowed_values"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "dicom_generic",
        "type": "dicom_generic_tag_type_check",
        "description": "Checks that a DICOM tag has the expected Value Representation (VR) type.",
        "required_params": ["tag", "expected_vr"],
        "optional_params": ["name", "severity", "description"],
    },
    # HL7 v2
    {
        "category": "hl7v2",
        "type": "hl7v2_field_exists",
        "description": "Checks that a field at an HL7 v2 path (e.g. PID-5.1) is present and non-empty.",
        "required_params": ["path"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "hl7v2",
        "type": "hl7v2_value_in_list",
        "description": "Checks that a field at an HL7 v2 path is one of the allowed values.",
        "required_params": ["path", "allowed"],
        "optional_params": ["case_insensitive", "name", "severity", "description"],
    },
    {
        "category": "hl7v2",
        "type": "hl7v2_regex_match",
        "description": "Checks that a field at an HL7 v2 path matches a regex pattern.",
        "required_params": ["path", "pattern"],
        "optional_params": ["name", "severity", "description"],
    },
    {
        "category": "hl7v2",
        "type": "hl7v2_numeric_range",
        "description": "Checks that a numeric field at an HL7 v2 path is within [min, max].",
        "required_params": ["path"],
        "optional_params": [
            "min",
            "max",
            "inclusive",
            "name",
            "severity",
            "description",
        ],
    },
    # HL7 v3 (XML/CDA)
    {
        "category": "hl7v3",
        "type": "hl7v3_xpath_exists",
        "description": "Checks that an XPath expression selects at least one node in HL7 v3 XML.",
        "required_params": ["xpath"],
        "optional_params": ["namespaces", "name", "severity", "description"],
    },
    {
        "category": "hl7v3",
        "type": "hl7v3_xpath_value_in_list",
        "description": "Checks that the value at an XPath expression is in the allowed list.",
        "required_params": ["xpath", "allowed"],
        "optional_params": [
            "namespaces",
            "attr",
            "case_insensitive",
            "name",
            "severity",
            "description",
        ],
    },
    {
        "category": "hl7v3",
        "type": "hl7v3_xpath_regex_match",
        "description": "Checks that the value at an XPath expression matches a regex pattern.",
        "required_params": ["xpath", "pattern"],
        "optional_params": ["namespaces", "attr", "name", "severity", "description"],
    },
    {
        "category": "hl7v3",
        "type": "hl7v3_xpath_numeric_range",
        "description": "Checks that a numeric value at an XPath expression is within [min, max].",
        "required_params": ["xpath"],
        "optional_params": [
            "min",
            "max",
            "inclusive",
            "namespaces",
            "attr",
            "name",
            "severity",
            "description",
        ],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_to_dict(r: Any) -> Dict[str, Any]:
    return {
        "name": r.name,
        "passed": r.passed,
        "message": r.message,
        "severity": (
            r.severity.value if hasattr(r.severity, "value") else str(r.severity)
        ),
        "context": r.context if r.context else {},
    }


def _load_spec_from_args(spec_path: Optional[str], spec_yaml: Optional[str]) -> Any:
    if spec_path and spec_yaml:
        raise ValueError("Provide spec_path or spec_yaml, not both.")
    if spec_path:
        return load_spec(spec_path)
    if spec_yaml:
        return load_spec_from_string(spec_yaml)
    raise ValueError("One of spec_path or spec_yaml is required.")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def run_guardrails(
    mode: str = "input",
    spec_path: Optional[str] = None,
    spec_yaml: Optional[str] = None,
    data_path: Optional[str] = None,
    data_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Run healthcare guardrail validators on a data file or inline content.

    Provide the spec as a file path (spec_path) or inline YAML string (spec_yaml).
    Provide the data as a file path (data_path) or inline text (data_content).
    DICOM files must use data_path. JSON, HL7, and XML can use either.

    Args:
        mode: Which validators to run — "input" or "output". Default "input".
        spec_path: Path to a YAML guardrail spec file on disk.
        spec_yaml: Inline YAML spec content as a string.
        data_path: Path to a data file (.dcm, .json, .xml, .hl7, etc.).
        data_content: Inline data — JSON string, HL7 v2 message, or XML text.

    Returns:
        Dict with "summary" (total/passed/failed/all_passed) and "results"
        (list of per-validator outcomes with name, passed, message, severity, context).
    """
    if mode not in {"input", "output"}:
        return {"error": f"Invalid mode {mode!r}. Must be 'input' or 'output'."}
    if not data_path and not data_content:
        return {"error": "One of data_path or data_content is required."}

    try:
        spec = _load_spec_from_args(spec_path, spec_yaml)
    except Exception as exc:
        return {"error": f"Failed to load spec: {exc}"}

    try:
        if data_path:
            data = load_data_from_path(Path(data_path))
        else:
            data = load_data_from_string(data_content)  # type: ignore[arg-type]
    except Exception as exc:
        return {"error": f"Failed to load data: {exc}"}

    validators = spec.input_validators if mode == "input" else spec.output_validators
    runner = GuardrailRunner(validators)
    results = runner.run(data)

    result_dicts = [_result_to_dict(r) for r in results]
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)

    return {
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "all_passed": passed_count == total,
        },
        "results": result_dicts,
    }


@mcp.tool()
def list_validator_types() -> Dict[str, Any]:
    """List all available guardrail validator types with their parameters.

    Returns a catalog of every validator type that can be used in a YAML spec,
    grouped by category (generic, dicom, dicom_generic, hl7v2, hl7v3).
    Includes each type's description and required/optional parameters.

    Returns:
        Dict with "validators" list and "categories" summary.
    """
    categories: Dict[str, List[str]] = {}
    for v in _VALIDATOR_CATALOG:
        cat = v["category"]
        categories.setdefault(cat, []).append(v["type"])

    return {
        "validators": _VALIDATOR_CATALOG,
        "categories": categories,
        "total": len(_VALIDATOR_CATALOG),
    }


@mcp.tool()
def validate_spec(
    spec_path: Optional[str] = None,
    spec_yaml: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate a guardrail YAML spec for correctness before running it.

    Attempts to parse and instantiate all validators defined in the spec.
    Returns errors for unknown validator types, missing required parameters,
    or YAML syntax problems.

    Args:
        spec_path: Path to a YAML guardrail spec file on disk.
        spec_yaml: Inline YAML spec content as a string.

    Returns:
        Dict with "valid" (bool), "errors" (list of strings),
        "input_count" and "output_count" (number of validators per section).
    """
    errors: List[str] = []

    try:
        spec = _load_spec_from_args(spec_path, spec_yaml)
        return {
            "valid": True,
            "errors": [],
            "input_count": len(spec.input_validators),
            "output_count": len(spec.output_validators),
        }
    except yaml.YAMLError as exc:
        errors.append(f"YAML syntax error: {exc}")
    except ValueError as exc:
        errors.append(str(exc))
    except Exception as exc:
        errors.append(f"Unexpected error: {exc}")

    return {"valid": False, "errors": errors, "input_count": 0, "output_count": 0}


@mcp.tool()
def describe_spec(
    spec_path: Optional[str] = None,
    spec_yaml: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse a guardrail spec and describe what each validator checks.

    Loads the spec and introspects each validator's name, description, and
    severity so an AI can understand what a spec does before running it.

    Args:
        spec_path: Path to a YAML guardrail spec file on disk.
        spec_yaml: Inline YAML spec content as a string.

    Returns:
        Dict with "input_validators" and "output_validators" lists, each
        containing {name, description, severity, validator_class} for every validator.
    """
    try:
        spec = _load_spec_from_args(spec_path, spec_yaml)
    except Exception as exc:
        return {"error": f"Failed to load spec: {exc}"}

    def _describe(validators: List[Any]) -> List[Dict[str, str]]:
        out = []
        for v in validators:
            severity_val = (
                v.severity.value if hasattr(v.severity, "value") else str(v.severity)
            )
            out.append(
                {
                    "name": getattr(v, "name", ""),
                    "description": getattr(v, "description", ""),
                    "severity": severity_val,
                    "validator_class": type(v).__name__,
                }
            )
        return out

    return {
        "input_validators": _describe(spec.input_validators),
        "output_validators": _describe(spec.output_validators),
        "input_count": len(spec.input_validators),
        "output_count": len(spec.output_validators),
    }


@mcp.tool()
def generate_spec_from_model_card(
    model_card_json: str,
) -> Dict[str, Any]:
    """Generate a guardrail YAML spec from an RT-AI-Model-Card JSON export.

    Parses an exported JSON from the RT-AI-Model-Card tool
    (https://github.com/MIRO-UCLouvain/RT-AI-Model-Card) and returns a
    guardrail YAML spec enforcing the training distribution at inference time.

    The following fields are extracted when present and parseable:
    - Modality (from technical_specifications.model_inputs) → dicom_modality
    - Age range (from training_data.age) → dicom_patient_age
    - Sex (from training_data.sex) → dicom_patient_sex
    - Patient positioning → dicom_patient_position
    - Slice thickness → dicom_slice_thickness
    - kVp → dicom_kvp

    Fields that cannot be reliably parsed from free text are skipped and
    listed in "skipped_fields".

    Args:
        model_card_json: The full JSON content of an RT-AI-Model-Card export
            as a string.

    Returns:
        Dict with:
        - "yaml": the generated guardrail YAML spec string
        - "extracted": summary of successfully extracted parameters
        - "skipped_fields": list of fields that could not be parsed
        - "error": present only on failure
    """
    import json as _json

    from .model_card import (
        model_card_to_extraction_summary,
        model_card_to_yaml,
    )

    try:
        card = _json.loads(model_card_json)
    except _json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON: {exc}"}

    if not isinstance(card, dict):
        return {"error": "model_card_json must be a JSON object"}

    try:
        yaml_str = model_card_to_yaml(card)
        summary = model_card_to_extraction_summary(card)
    except Exception as exc:
        return {"error": f"Failed to generate spec: {exc}"}

    return {
        "yaml": yaml_str,
        "extracted": summary["extracted"],
        "skipped_fields": summary["skipped_fields"],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
