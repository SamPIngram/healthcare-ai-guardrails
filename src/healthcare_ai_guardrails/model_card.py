"""RT-AI-Model-Card integration for automatic guardrail spec generation.

Parses an exported RT-AI-Model-Card JSON file
(https://github.com/MIRO-UCLouvain/RT-AI-Model-Card) and converts it
into a healthcare-ai-guardrails YAML spec that enforces the training
data distribution at inference time.

Example usage::

    from healthcare_ai_guardrails.model_card import load_model_card, model_card_to_yaml

    card = load_model_card("model_card.json")
    yaml_spec = model_card_to_yaml(card)
    print(yaml_spec)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .config import load_spec_from_string, Spec

# ---------------------------------------------------------------------------
# Field parsers
# ---------------------------------------------------------------------------

# DICOM standard patient position codes (used both for the text-map and regex)
_DICOM_POSITIONS = {
    "HFS",
    "HFP",
    "FFS",
    "FFP",
    "HFDR",
    "HFDL",
    "FFDR",
    "FFDL",
    "SITTING",
    "LLD",
    "RLD",
}

# Pre-compiled regex built from _DICOM_POSITIONS so the two stay in sync.
# Longer codes are tried first to avoid partial matches (e.g. "HFS" before "HF").
_POSITION_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(_DICOM_POSITIONS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Text-description → DICOM code mappings (lowercase keys)
_POSITION_TEXT_MAP: Dict[str, str] = {
    "head first supine": "HFS",
    "head first prone": "HFP",
    "feet first supine": "FFS",
    "feet first prone": "FFP",
    "head first decubitus right": "HFDR",
    "head first decubitus left": "HFDL",
    "feet first decubitus right": "FFDR",
    "feet first decubitus left": "FFDL",
}

# Modality normalisation aliases (uppercase keys).
# Compound strings like "PET/CT" are split on "/" before lookup so both
# components are preserved — do NOT add compound keys here.
_MODALITY_ALIASES: Dict[str, str] = {
    "MRI": "MR",
    "PET": "PT",
    "XRAY": "DX",
    "X-RAY": "DX",
    "NUCLEAR MEDICINE": "NM",
}


def _parse_age_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Return (min_years, max_years) parsed from a free-text age description.

    Supports patterns such as:
    - "18-75 years", "18–75", "18 to 75 years"
    - ">= 18 years", "≥18", "> 18"
    - "<= 80 years", "≤80", "< 80 years"
    - "adults (18+)"

    Returns (None, None) if no age information can be extracted.
    """
    if not text or not text.strip():
        return None, None

    t = text.strip()

    # Explicit range: "18-75 years" / "18 to 75" / "18–75"
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|y\.?o\.?|yrs?)?",
        t,
        re.IGNORECASE,
    )
    if range_match:
        lo, hi = float(range_match.group(1)), float(range_match.group(2))
        return (lo, hi) if lo <= hi else (hi, lo)

    # Lower bound only: ">= 18", "≥18", "> 18", "adults (18+)"
    lower_match = re.search(
        r"(?:[≥≧]|>=|>)\s*(\d+(?:\.\d+)?)\s*(?:years?|y\.?o\.?|yrs?)?|"
        r"(\d+)\+\s*(?:years?|y\.?o\.?|yrs?)?",
        t,
        re.IGNORECASE,
    )
    if lower_match:
        val = lower_match.group(1) or lower_match.group(2)
        return float(val), None

    # Upper bound only: "<= 80", "≤80", "< 80"
    upper_match = re.search(
        r"(?:[≤≦]|<=|<)\s*(\d+(?:\.\d+)?)\s*(?:years?|y\.?o\.?|yrs?)?",
        t,
        re.IGNORECASE,
    )
    if upper_match:
        return None, float(upper_match.group(1))

    return None, None


def _parse_sex(text: str) -> List[str]:
    """Return a list of DICOM sex codes parsed from a free-text description.

    Recognised codes: M, F, O.
    Returns empty list if nothing can be determined.
    """
    if not text or not text.strip():
        return []

    t = text.lower()
    result: List[str] = []

    # Shorthand patterns first (before keyword matching to avoid false positives)
    # "M/F", "M, F", "M & F"
    if re.search(r"\bm\s*[/,&]\s*f\b|\bf\s*[/,&]\s*m\b", t):
        return ["M", "F"]
    if re.search(r"\bm\s*[/,&]\s*f\s*[/,&]\s*o\b", t):
        return ["M", "F", "O"]

    # Keyword-based
    has_male = bool(re.search(r"\bmale\b|\bmen\b|\bman\b", t))
    has_female = bool(re.search(r"\bfemale\b|\bwomen\b|\bwoman\b", t))
    # "both" alone is unambiguous; "all" is only safe when followed by
    # "genders" or "sexes" (e.g. "all male" must NOT match).
    has_both = bool(re.search(r"\bboth\b|\bmix|\ball\s+(?:genders?|sexes?)", t))
    has_other = bool(re.search(r"\bother\b", t))

    if has_both or (has_male and has_female):
        result = ["M", "F"]
    elif has_male:
        result = ["M"]
    elif has_female:
        result = ["F"]
    else:
        # Try single-letter codes: standalone "M" or "F"
        if re.search(r"\bm\b", t):
            result.append("M")
        if re.search(r"\bf\b", t):
            result.append("F")

    if has_other and "O" not in result:
        result.append("O")

    return result


def _normalise_modality_list(raw: Any) -> List[str]:
    """Normalise a raw list of modality strings to DICOM codes.

    Compound strings like ``"PET/CT"`` are split on ``"/"`` before alias
    lookup so that all modalities are preserved in the output
    (``["PT", "CT"]`` rather than losing one of them).
    """
    if not isinstance(raw, list):
        return []
    normalised: List[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        # Split compound modalities (e.g. "PET/CT" → ["PET", "CT"])
        for part in item.split("/"):
            code = part.strip().upper()
            code = _MODALITY_ALIASES.get(code, code)
            if code and code not in normalised:
                normalised.append(code)
    return normalised


def _parse_modalities(model_card: Dict[str, Any]) -> List[str]:
    """Extract and normalise modality codes from technical_specifications.model_inputs."""
    tech = model_card.get("technical_specifications", {})
    return _normalise_modality_list(tech.get("model_inputs", []))


def _parse_output_modalities(model_card: Dict[str, Any]) -> List[str]:
    """Extract and normalise modality codes from technical_specifications.model_outputs."""
    tech = model_card.get("technical_specifications", {})
    return _normalise_modality_list(tech.get("model_outputs", []))


def _parse_patient_positions(text: str) -> List[str]:
    """Extract DICOM patient position codes from a free-text string.

    Recognises standard 4-letter codes (HFS, HFP, …) and common
    natural-language descriptions.
    """
    if not text or not text.strip():
        return []

    t = text.strip()
    found: List[str] = []

    # Try natural-language descriptions first (longest match first)
    t_lower = t.lower()
    for desc, code in sorted(_POSITION_TEXT_MAP.items(), key=lambda x: -len(x[0])):
        if desc in t_lower and code not in found:
            found.append(code)

    # Extract standard uppercase codes using the pre-compiled pattern
    for code in _POSITION_PATTERN.findall(t):
        upper = code.upper()
        if upper not in found:
            found.append(upper)

    return found


def _parse_slice_thickness(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract a slice thickness range (mm) from free-text acquisition parameters.

    Supports:
    - "slice thickness: 1-3mm", "slice thickness 1.5mm"
    - "1mm slice", "3 mm slices"
    - "1-3 mm"
    """
    if not text or not text.strip():
        return None, None

    t = text

    # "slice thickness: 1-3mm" or "slice thickness 1 to 3 mm"
    range_match = re.search(
        r"slice\s*(?:thickness)?\s*:?\s*(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*mm",
        t,
        re.IGNORECASE,
    )
    if range_match:
        lo, hi = float(range_match.group(1)), float(range_match.group(2))
        return (lo, hi) if lo <= hi else (hi, lo)

    # Single value: "slice thickness: 1.5mm"
    single_match = re.search(
        r"slice\s*(?:thickness)?\s*:?\s*(\d+(?:\.\d+)?)\s*mm",
        t,
        re.IGNORECASE,
    )
    if single_match:
        val = float(single_match.group(1))
        return val, val

    # "1mm slice" / "3mm slices"
    mm_slice_match = re.search(
        r"(\d+(?:\.\d+)?)\s*mm\s*(?:slices?|thick)",
        t,
        re.IGNORECASE,
    )
    if mm_slice_match:
        val = float(mm_slice_match.group(1))
        return val, val

    return None, None


def _parse_kvp(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract a kVp range from free-text acquisition parameters.

    Supports:
    - "120 kVp", "kVp: 120", "100-140 kVp", "kVp 100-140"
    """
    if not text or not text.strip():
        return None, None

    t = text

    # "100-140 kVp" or "kVp: 100-140"
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*k[Vv][Pp]|"
        r"k[Vv][Pp]\s*:?\s*(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)",
        t,
        re.IGNORECASE,
    )
    if range_match:
        if range_match.group(1):
            lo, hi = float(range_match.group(1)), float(range_match.group(2))
        else:
            lo, hi = float(range_match.group(3)), float(range_match.group(4))
        return (lo, hi) if lo <= hi else (hi, lo)

    # Single value: "120 kVp" or "kVp: 120"
    single_match = re.search(
        r"(\d+(?:\.\d+)?)\s*k[Vv][Pp]|k[Vv][Pp]\s*:?\s*(\d+(?:\.\d+)?)",
        t,
        re.IGNORECASE,
    )
    if single_match:
        val = float(single_match.group(1) or single_match.group(2))
        return val, val

    return None, None


def _parse_scanner_models(text: str) -> List[str]:
    """Extract individual scanner model names from a comma-separated free-text string.

    The RT-AI-Model-Card ``scanner_model`` field typically contains one or more
    make/model strings separated by commas, e.g.::

        "Siemens SOMATOM Definition AS+, GE Discovery CT750 HD"

    Each value is returned trimmed.  The caller should use these as the
    ``allowed_values`` for a ``dicom_generic_value_in_list`` validator on the
    ``ManufacturerModelName`` DICOM tag — note that DICOM tag values may not
    include the manufacturer prefix, so review the generated validator before
    use.

    Returns an empty list if the text is blank.
    """
    if not text or not text.strip():
        return []
    return [s.strip() for s in text.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Spec/YAML generation
# ---------------------------------------------------------------------------


def _build_spec_entries(
    model_card: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Build input and output validator dicts plus an extraction summary.

    Returns ``(input_entries, output_entries, extracted_summary)``.
    """
    input_entries: List[Dict[str, Any]] = []
    output_entries: List[Dict[str, Any]] = []
    extracted: Dict[str, Any] = {}
    skipped: List[str] = []

    training = model_card.get("training_data", {})
    model_name: str = (
        model_card.get("model_basic_information", {}).get("name", "")
        or model_card.get("card_metadata", {}).get("version_number", "")
        or "unknown"
    )

    # --- Input modality ---
    modalities = _parse_modalities(model_card)
    if modalities:
        input_entries.append(
            {
                "type": "dicom_modality",
                "name": "allowed_modality",
                "description": f"Modality must match training data for model: {model_name}",
                "allowed": modalities,
                "severity": "error",
            }
        )
        extracted["modalities"] = modalities
    else:
        skipped.append("modalities")

    # --- Age ---
    age_text = str(training.get("age", "") or "")
    min_age, max_age = _parse_age_range(age_text)
    if min_age is not None or max_age is not None:
        entry: Dict[str, Any] = {
            "type": "dicom_patient_age",
            "name": "age_in_training_bounds",
            "description": f"Patient age within training distribution ({age_text.strip()})",
            "severity": "warning",
        }
        if min_age is not None:
            entry["min_years"] = min_age
        if max_age is not None:
            entry["max_years"] = max_age
        input_entries.append(entry)
        extracted["age_range"] = [min_age, max_age]
    else:
        skipped.append("age")

    # --- Sex ---
    sex_text = str(training.get("sex", "") or "")
    sex_codes = _parse_sex(sex_text)
    if sex_codes:
        input_entries.append(
            {
                "type": "dicom_patient_sex",
                "name": "allowed_patient_sex",
                "description": f"Patient sex within training distribution ({sex_text.strip()})",
                "allowed": sex_codes,
                "severity": "warning",
            }
        )
        extracted["sex"] = sex_codes
    else:
        skipped.append("sex")

    # --- Per-modality scan parameters (inputs only) ---
    io_specs: Any = training.get("inputs_outputs_technical_specifications", [])
    if isinstance(io_specs, list):
        all_positions: List[str] = []
        all_slice_thicknesses: List[Tuple[Optional[float], Optional[float]]] = []
        all_kvps: List[Tuple[Optional[float], Optional[float]]] = []
        all_scanner_models: List[str] = []

        for spec_item in io_specs:
            if not isinstance(spec_item, dict):
                continue
            if spec_item.get("source") != "model_inputs":
                continue

            pos_text = str(spec_item.get("patient_positioning", "") or "")
            positions = _parse_patient_positions(pos_text)
            for p in positions:
                if p not in all_positions:
                    all_positions.append(p)

            acq_text = str(spec_item.get("scan_acquisition_parameters", "") or "")
            st_range = _parse_slice_thickness(acq_text)
            if st_range != (None, None):
                all_slice_thicknesses.append(st_range)

            kvp_range = _parse_kvp(acq_text)
            if kvp_range != (None, None):
                all_kvps.append(kvp_range)

            scanner_text = str(spec_item.get("scanner_model", "") or "")
            for model in _parse_scanner_models(scanner_text):
                if model not in all_scanner_models:
                    all_scanner_models.append(model)

        if all_positions:
            input_entries.append(
                {
                    "type": "dicom_patient_position",
                    "name": "allowed_patient_position",
                    "description": "Patient position must match training data",
                    "allowed": all_positions,
                    "severity": "warning",
                }
            )
            extracted["patient_positions"] = all_positions
        else:
            skipped.append("patient_positioning")

        if all_slice_thicknesses:
            # Use the broadest range across all modalities
            mins = [lo for lo, _ in all_slice_thicknesses if lo is not None]
            maxs = [hi for _, hi in all_slice_thicknesses if hi is not None]
            st_entry: Dict[str, Any] = {
                "type": "dicom_slice_thickness",
                "name": "slice_thickness_in_training_bounds",
                "description": "Slice thickness within training distribution",
                "severity": "warning",
            }
            if mins:
                st_entry["min_mm"] = min(mins)
            if maxs:
                st_entry["max_mm"] = max(maxs)
            input_entries.append(st_entry)
            extracted["slice_thickness_mm"] = [
                st_entry.get("min_mm"),
                st_entry.get("max_mm"),
            ]
        else:
            skipped.append("slice_thickness")

        if all_kvps:
            mins_kvp = [lo for lo, _ in all_kvps if lo is not None]
            maxs_kvp = [hi for _, hi in all_kvps if hi is not None]
            kvp_entry: Dict[str, Any] = {
                "type": "dicom_kvp",
                "name": "kvp_in_training_bounds",
                "description": "kVp within training distribution",
                "severity": "warning",
            }
            if mins_kvp:
                kvp_entry["min_kvp"] = min(mins_kvp)
            if maxs_kvp:
                kvp_entry["max_kvp"] = max(maxs_kvp)
            input_entries.append(kvp_entry)
            extracted["kvp"] = [kvp_entry.get("min_kvp"), kvp_entry.get("max_kvp")]
        else:
            skipped.append("kvp")

        if all_scanner_models:
            input_entries.append(
                {
                    "type": "dicom_generic_value_in_list",
                    "name": "allowed_scanner_model",
                    "description": (
                        "Scanner model must match training data. "
                        "Review ManufacturerModelName values — DICOM tags may omit "
                        "the manufacturer prefix (e.g. 'SOMATOM Definition AS+' not "
                        "'Siemens SOMATOM Definition AS+')."
                    ),
                    "tag": "ManufacturerModelName",
                    "allowed_values": all_scanner_models,
                    "severity": "warning",
                }
            )
            extracted["scanner_models"] = all_scanner_models
        else:
            skipped.append("scanner_model")

    # --- Output modality ---
    # Only emit if model_outputs is explicitly present in the card.
    tech = model_card.get("technical_specifications", {})
    if "model_outputs" in tech:
        output_modalities = _parse_output_modalities(model_card)
        if output_modalities:
            output_entries.append(
                {
                    "type": "dicom_modality",
                    "name": "allowed_output_modality",
                    "description": (
                        f"Output modality must match model specification for: {model_name}"
                    ),
                    "allowed": output_modalities,
                    "severity": "error",
                }
            )
            extracted["output_modalities"] = output_modalities
        else:
            skipped.append("output_modalities")

    extracted["skipped_fields"] = skipped
    return input_entries, output_entries, extracted


def model_card_to_yaml(model_card: Dict[str, Any]) -> str:
    """Convert an RT-AI-Model-Card dict into a guardrail YAML spec string.

    Fields that cannot be reliably parsed from free text are silently skipped;
    they are listed in a comment block at the top of the generated YAML so the
    user knows what to add manually.

    :param model_card: Parsed RT-AI-Model-Card JSON as a dict.
    :return: YAML string suitable for use with :func:`load_spec_from_string`.
    """
    input_entries, output_entries, summary = _build_spec_entries(model_card)
    skipped = summary.get("skipped_fields", [])

    model_name: str = (
        model_card.get("model_basic_information", {}).get("name", "") or "unknown"
    )
    # Sanitize: a newline in the name would break the YAML comment and could
    # inject arbitrary content into the generated spec.
    model_name = model_name.replace("\r", " ").replace("\n", " ")

    header_lines = [
        f"# Auto-generated from RT-AI-Model-Card: {model_name}",
        "# Edit as needed before use in production.",
    ]

    if skipped:
        header_lines.append(
            f"# Fields not extracted (unparseable or absent): {', '.join(skipped)}"
        )
        header_lines.append(
            "# Review these fields and add validators manually if needed."
        )

    header_lines.append("")

    spec_dict: Dict[str, Any] = {"input": input_entries, "output": output_entries}
    yaml_body = yaml.dump(
        spec_dict, default_flow_style=False, allow_unicode=True, sort_keys=False
    )

    return "\n".join(header_lines) + yaml_body


def model_card_to_spec(model_card: Dict[str, Any]) -> Spec:
    """Convert an RT-AI-Model-Card dict into a :class:`Spec` object.

    :param model_card: Parsed RT-AI-Model-Card JSON as a dict.
    :return: A :class:`~healthcare_ai_guardrails.config.Spec` ready for use
        with :class:`~healthcare_ai_guardrails.runner.GuardrailRunner`.
    """
    yaml_str = model_card_to_yaml(model_card)
    return load_spec_from_string(yaml_str)


def load_model_card(path: str | Path) -> Dict[str, Any]:
    """Load an RT-AI-Model-Card JSON export from *path*.

    :param path: Path to a ``.json`` file exported from the RT-AI-Model-Card
        tool (https://github.com/MIRO-UCLouvain/RT-AI-Model-Card).
    :return: The model card as a plain Python dict.
    :raises ValueError: If the file is not valid JSON or not a JSON object.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a JSON object at top level, got {type(data).__name__}"
        )
    return data


def model_card_to_extraction_summary(model_card: Dict[str, Any]) -> Dict[str, Any]:
    """Return a summary of what was extracted from the model card.

    Useful for debugging or for the MCP tool response.

    :param model_card: Parsed RT-AI-Model-Card JSON as a dict.
    :return: Dict with keys ``extracted`` and ``skipped_fields``.
    """
    _, __, extracted = _build_spec_entries(model_card)
    skipped = extracted.pop("skipped_fields", [])
    return {"extracted": extracted, "skipped_fields": skipped}
