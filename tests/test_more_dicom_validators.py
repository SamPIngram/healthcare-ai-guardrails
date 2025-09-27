from healthcare_ai_guardrails.testing.dicom_factory import create_test_dicom
from healthcare_ai_guardrails.validators.dicom import (
    DICOMSOPClassCheck,
    DICOMBodyPartExaminedCheck,
    DICOMPhotometricInterpretationCheck,
    DICOMPixelIntensityRangeCheck,
)


def test_sop_class_allowed():
    ds = create_test_dicom(sop_class_uid="1.2.3.4")
    v = DICOMSOPClassCheck(allowed_uids=["1.2.3.4"])
    assert v.validate(ds).passed is True
    v2 = DICOMSOPClassCheck(allowed_uids=["9.9.9"])
    assert v2.validate(ds).passed is False


def test_body_part_examined_allowed():
    ds = create_test_dicom(body_part="HEAD")
    v = DICOMBodyPartExaminedCheck(allowed=["HEAD", "CHEST"])
    assert v.validate(ds).passed is True
    v2 = DICOMBodyPartExaminedCheck(allowed=["CHEST"])
    assert v2.validate(ds).passed is False


def test_photometric_interpretation_allowed():
    ds = create_test_dicom(photometric="MONOCHROME2")
    v = DICOMPhotometricInterpretationCheck(allowed=["MONOCHROME2"])
    assert v.validate(ds).passed is True
    v2 = DICOMPhotometricInterpretationCheck(allowed=["RGB"])
    assert v2.validate(ds).passed is False


def test_pixel_intensity_range():
    ds = create_test_dicom(shape=(8, 8), pixel_dtype="uint16")
    v = DICOMPixelIntensityRangeCheck(min_value=0, max_value=4095)
    assert v.validate(ds).passed is True
    v2 = DICOMPixelIntensityRangeCheck(min_value=100, max_value=200)
    assert v2.validate(ds).passed is False
