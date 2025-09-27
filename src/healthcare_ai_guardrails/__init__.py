"""
Healthcare AI Guardrails package.

Exposes minimal public API for defining and running validation checks
on inputs/outputs, with DICOM utilities.
"""

from .runner import GuardrailRunner, ValidationResult, Severity
from .validators.basic import RangeCheck, ChoiceCheck, RequiredFieldsCheck
from .validators.dicom import (
    DICOMPatientAgeCheck,
    DICOMModalityCheck,
    DICOMPatientSexCheck,
    DICOMSliceThicknessCheck,
    DICOMPixelSpacingCheck,
    DICOMImageOrientationCheck,
    DICOMSOPClassCheck,
    DICOMBodyPartExaminedCheck,
    DICOMPhotometricInterpretationCheck,
    DICOMPixelIntensityRangeCheck,
)
from .config import load_spec

__all__ = [
    "GuardrailRunner",
    "ValidationResult",
    "Severity",
    "RangeCheck",
    "ChoiceCheck",
    "RequiredFieldsCheck",
    "DICOMPatientAgeCheck",
    "DICOMModalityCheck",
    "DICOMPatientSexCheck",
    "DICOMSliceThicknessCheck",
    "DICOMPixelSpacingCheck",
    "DICOMImageOrientationCheck",
    "DICOMSOPClassCheck",
    "DICOMBodyPartExaminedCheck",
    "DICOMPhotometricInterpretationCheck",
    "DICOMPixelIntensityRangeCheck",
    "load_spec",
]
