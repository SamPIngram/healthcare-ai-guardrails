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
    DICOMPatientSexCheck,
    DICOMSliceThicknessCheck,
    DICOMPixelSpacingCheck,
    DICOMImageOrientationCheck,
    DICOMSOPClassCheck,
    DICOMBodyPartExaminedCheck,
    DICOMPhotometricInterpretationCheck,
    DICOMPixelIntensityRangeCheck,
)
from .validators.schema import JSONSchemaCheck


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
    if t == "dicom_patient_age":
        return DICOMPatientAgeCheck(
            name=name,
            min_years=entry.get("min_years"),
            max_years=entry.get("max_years"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t == "dicom_modality":
        return DICOMModalityCheck(
            name=name,
            allowed_modalities=entry.get("allowed", []),
            severity=severity,
            description=desc,
        )
    if t == "dicom_patient_sex":
        return DICOMPatientSexCheck(
            name=name,
            allowed=entry.get("allowed", ["M", "F", "O"]),
            severity=severity,
            description=desc,
        )
    if t == "dicom_slice_thickness":
        return DICOMSliceThicknessCheck(
            name=name,
            min_mm=entry.get("min_mm"),
            max_mm=entry.get("max_mm"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t == "dicom_pixel_spacing":
        return DICOMPixelSpacingCheck(
            name=name,
            min_mm=entry.get("min_mm"),
            max_mm=entry.get("max_mm"),
            inclusive=entry.get("inclusive", True),
            severity=severity,
            description=desc,
        )
    if t == "dicom_image_orientation":
        return DICOMImageOrientationCheck(
            name=name,
            tolerance=entry.get("tolerance", 1e-3),
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
    if t == "json_schema":
        return JSONSchemaCheck(
            name=name,
            schema=entry.get("schema"),
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
