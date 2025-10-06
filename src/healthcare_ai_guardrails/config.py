from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .runner import Severity
from .validators.basic import RangeCheck, ChoiceCheck, RequiredFieldsCheck
from .validators.dicom import (
    DICOMModalityCheck,
    DICOMPatientAgeCheck,
    DICOMPatientPositionCheck,
    DICOMPatientSexCheck,
    DICOMSliceThicknessCheck,
    DICOMPixelSpacingCheck,
    DICOMImageOrientationCheck,
    DICOMSOPClassCheck,
    DICOMBodyPartExaminedCheck,
    DICOMPhotometricInterpretationCheck,
    DICOMPixelIntensityRangeCheck,
    DICOMProtocolNameCheck,
    DICOMRTStructureCheck,
    DICOMKVPCheck,
    DICOMTubeCurrentCheck,
    DICOMExposureTimeCheck,
)
from .validators.schema import JSONSchemaCheck
from .validators.generic_dicom import (
    DICOMGenericNumericRangeCheck,
    DICOMGenericValueInListCheck,
    DICOMGenericTagTypeCheck,
)
from .validators.hl7 import (
    HL7FieldExistsCheck,
    HL7ValueInListCheck,
    HL7RegexMatchCheck,
    HL7NumericRangeCheck,
)
from .validators.hl7v3 import (
    HL7v3XPathExistsCheck,
    HL7v3XPathValueInListCheck,
    HL7v3XPathRegexMatchCheck,
    HL7v3XPathNumericRangeCheck,
)


ValidatorObj = Any


@dataclass
class Spec:
    input_validators: List[ValidatorObj]
    output_validators: List[ValidatorObj]


def _severity(s: str | None) -> Severity:
    if not s:
        return Severity.WARNING
    s = s.lower()
    return {
        "info": Severity.INFO,
        "warning": Severity.WARNING,
        "error": Severity.ERROR,
    }.get(s, Severity.WARNING)


def _build_validator(entry: Dict[str, Any]) -> ValidatorObj:
    t = entry.get("type")
    name = entry.get("name", t)
    severity = _severity(entry.get("severity"))
    desc = entry.get("description", "")
    if t == "range":
        return RangeCheck(
            name=name,
            path=entry.get("path"),
            min_value=entry.get("min"),
            max_value=entry.get("max"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t == "choice":
        return ChoiceCheck(
            name=name,
            path=entry.get("path"),
            allowed=entry.get("allowed", []),
            case_insensitive=entry.get("case_insensitive", False),
            severity=severity,
            description=desc,
        )
    if t == "required_fields":
        return RequiredFieldsCheck(
            name=name,
            paths=entry.get("paths", []),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_patient_age", "dicom_patient_age_range"):
        return DICOMPatientAgeCheck(
            name=name,
            min_years=entry.get("min_years"),
            max_years=entry.get("max_years"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_modality", "dicom_modality_allowed"):
        return DICOMModalityCheck(
            name=name,
            allowed_modalities=entry.get("allowed", []),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_patient_sex", "dicom_patient_sex_allowed"):
        return DICOMPatientSexCheck(
            name=name,
            allowed=entry.get("allowed", ["M", "F", "O"]),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_patient_position", "dicom_patient_position_allowed"):
        return DICOMPatientPositionCheck(
            name=name,
            allowed=entry.get("allowed", []),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_slice_thickness", "dicom_slice_thickness_range"):
        return DICOMSliceThicknessCheck(
            name=name,
            min_mm=entry.get("min_mm"),
            max_mm=entry.get("max_mm"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_pixel_spacing", "dicom_pixel_spacing_range"):
        return DICOMPixelSpacingCheck(
            name=name,
            min_mm=entry.get("min_mm"),
            max_mm=entry.get("max_mm"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_image_orientation", "dicom_image_orientation_sane"):
        return DICOMImageOrientationCheck(
            name=name,
            tolerance=entry.get("tolerance", 1e-3),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_protocol_name", "dicom_protocol_name_allowed"):
        return DICOMProtocolNameCheck(
            name=name,
            allowed=entry.get("allowed", []),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_rt_structure", "dicom_rt_structure_present"):
        return DICOMRTStructureCheck(
            name=name,
            required_rois=entry.get("required_rois", []),
            severity=severity,
            description=desc,
        )
    if t == "dicom_sop_class":
        return DICOMSOPClassCheck(
            name=name,
            allowed_uids=entry.get("allowed", []),
            severity=severity,
            description=desc,
        )
    if t == "dicom_body_part_examined":
        return DICOMBodyPartExaminedCheck(
            name=name,
            allowed=entry.get("allowed", []),
            severity=severity,
            description=desc,
        )
    if t == "dicom_photometric_interpretation":
        return DICOMPhotometricInterpretationCheck(
            name=name,
            allowed=entry.get("allowed", []),
            severity=severity,
            description=desc,
        )
    if t == "dicom_pixel_intensity_range":
        return DICOMPixelIntensityRangeCheck(
            name=name,
            min_value=entry.get("min"),
            max_value=entry.get("max"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_kvp", "dicom_kvp_range"):
        return DICOMKVPCheck(
            name=name,
            min_kvp=entry.get("min_kvp"),
            max_kvp=entry.get("max_kvp"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_tube_current", "dicom_tube_current_range"):
        return DICOMTubeCurrentCheck(
            name=name,
            min_ma=entry.get("min_ma"),
            max_ma=entry.get("max_ma"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t in ("dicom_exposure_time", "dicom_exposure_time_range"):
        return DICOMExposureTimeCheck(
            name=name,
            min_ms=entry.get("min_ms"),
            max_ms=entry.get("max_ms"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t == "json_schema":
        return JSONSchemaCheck(
            name=name,
            schema=entry.get("schema"),
            severity=severity,
            description=desc,
        )
    # HL7 v2 validators
    if t in ("hl7v2_field_exists", "hl7_field_exists", "hl7_required_field"):
        return HL7FieldExistsCheck(
            name=name,
            path=entry.get("path"),
            severity=severity,
            description=desc,
        )
    if t in ("hl7v2_value_in_list", "hl7_value_in_list", "hl7_choice"):
        return HL7ValueInListCheck(
            name=name,
            path=entry.get("path"),
            allowed=entry.get("allowed", []),
            case_insensitive=entry.get("case_insensitive", False),
            severity=severity,
            description=desc,
        )
    if t in ("hl7v2_regex_match", "hl7_regex_match", "hl7_pattern"):
        return HL7RegexMatchCheck(
            name=name,
            path=entry.get("path"),
            pattern=entry.get("pattern", ".*"),
            severity=severity,
            description=desc,
        )
    if t in ("hl7v2_numeric_range", "hl7_numeric_range", "hl7_range"):
        return HL7NumericRangeCheck(
            name=name,
            path=entry.get("path"),
            min_value=entry.get("min"),
            max_value=entry.get("max"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    # HL7 v3 (XML/XPath) validators
    if t in ("hl7v3_xpath_exists", "hl7v3_required"):
        return HL7v3XPathExistsCheck(
            name=name,
            xpath=entry.get("xpath"),
            namespaces=entry.get("namespaces"),
            severity=severity,
            description=desc,
        )
    if t in ("hl7v3_xpath_value_in_list", "hl7v3_xpath_choice"):
        return HL7v3XPathValueInListCheck(
            name=name,
            xpath=entry.get("xpath"),
            allowed=entry.get("allowed", []),
            namespaces=entry.get("namespaces"),
            case_insensitive=entry.get("case_insensitive", False),
            attr=entry.get("attr"),
            severity=severity,
            description=desc,
        )
    if t in ("hl7v3_xpath_regex_match", "hl7v3_xpath_pattern"):
        return HL7v3XPathRegexMatchCheck(
            name=name,
            xpath=entry.get("xpath"),
            pattern=entry.get("pattern", ".*"),
            namespaces=entry.get("namespaces"),
            attr=entry.get("attr"),
            severity=severity,
            description=desc,
        )
    if t in ("hl7v3_xpath_numeric_range", "hl7v3_xpath_range"):
        return HL7v3XPathNumericRangeCheck(
            name=name,
            xpath=entry.get("xpath"),
            min_value=entry.get("min"),
            max_value=entry.get("max"),
            inclusive=entry.get("inclusive", True),
            namespaces=entry.get("namespaces"),
            attr=entry.get("attr"),
            severity=severity,
            description=desc,
        )
    if t == "dicom_generic_numeric_range":
        return DICOMGenericNumericRangeCheck(
            name=name,
            tag=entry.get("tag"),
            unit=entry.get("unit", ""),
            min_val=entry.get("min_val"),
            max_val=entry.get("max_val"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t == "dicom_generic_value_in_list":
        return DICOMGenericValueInListCheck(
            name=name,
            tag=entry.get("tag"),
            allowed_values=entry.get("allowed_values", []),
            severity=severity,
            description=desc,
        )
    if t == "dicom_generic_tag_type_check":
        return DICOMGenericTagTypeCheck(
            name=name,
            tag=entry.get("tag"),
            expected_vr=entry.get("expected_vr"),
            severity=severity,
            description=desc,
        )
    raise ValueError(f"Unknown validator type: {t}")


def load_spec(path: str | Path) -> Spec:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    input_entries = cfg.get("input", [])
    output_entries = cfg.get("output", [])
    input_validators = [_build_validator(e) for e in input_entries]
    output_validators = [_build_validator(e) for e in output_entries]
    return Spec(input_validators=input_validators, output_validators=output_validators)
