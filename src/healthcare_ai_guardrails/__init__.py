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
    DICOMProtocolNameCheck,
    DICOMRTStructureCheck,
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
    "DICOMProtocolNameCheck",
    "DICOMRTStructureCheck",
    "HL7FieldExistsCheck",
    "HL7ValueInListCheck",
    "HL7RegexMatchCheck",
    "HL7NumericRangeCheck",
    "HL7v3XPathExistsCheck",
    "HL7v3XPathValueInListCheck",
    "HL7v3XPathRegexMatchCheck",
    "HL7v3XPathNumericRangeCheck",
    "load_spec",
]
