from healthcare_ai_guardrails.validators.dicom import (
    DICOMPatientSexCheck,
    DICOMSliceThicknessCheck,
    DICOMPixelSpacingCheck,
    DICOMImageOrientationCheck,
    DICOMKVPCheck,
    DICOMTubeCurrentCheck,
    DICOMExposureTimeCheck,
    DICOMProtocolNameCheck,
    DICOMPatientPositionCheck,
)


class FakeDS(dict):
    def __getattr__(self, item):
        return self.get(item)


def test_patient_sex_check():
    ds = FakeDS(PatientSex="M")
    v = DICOMPatientSexCheck(allowed=["M", "F", "O"])
    assert v.validate(ds).passed is True
    ds2 = FakeDS(PatientSex="X")
    assert v.validate(ds2).passed is False


def test_slice_thickness_check():
    ds = FakeDS(SliceThickness="1.0")
    v = DICOMSliceThicknessCheck(min_mm=0.5, max_mm=5)
    assert v.validate(ds).passed is True
    ds2 = FakeDS(SliceThickness="10.0")
    assert v.validate(ds2).passed is False


def test_pixel_spacing_check():
    ds = FakeDS(PixelSpacing=[0.5, 0.6])
    v = DICOMPixelSpacingCheck(min_mm=0.2, max_mm=2.0)
    assert v.validate(ds).passed is True
    ds2 = FakeDS(PixelSpacing=[0.05, 0.6])
    assert v.validate(ds2).passed is False


def test_image_orientation_check():
    ds = FakeDS(ImageOrientationPatient=[1, 0, 0, 0, 1, 0])
    v = DICOMImageOrientationCheck(tolerance=1e-3)
    assert v.validate(ds).passed is True
    ds2 = FakeDS(ImageOrientationPatient=[1, 0, 0, 1, 0, 0])  # not orthogonal
    assert v.validate(ds2).passed is False


def test_kvp_check():
    ds = FakeDS(KVP="120")
    v = DICOMKVPCheck(min_kvp=80, max_kvp=140)
    assert v.validate(ds).passed is True
    ds2 = FakeDS(KVP="70")
    assert v.validate(ds2).passed is False


def test_tube_current_check():
    ds = FakeDS(XRayTubeCurrent="200")
    v = DICOMTubeCurrentCheck(min_ma=100, max_ma=500)
    assert v.validate(ds).passed is True
    ds2 = FakeDS(XRayTubeCurrent="50")
    assert v.validate(ds2).passed is False


def test_exposure_time_check():
    ds = FakeDS(ExposureTime="100")
    v = DICOMExposureTimeCheck(min_ms=50, max_ms=200)
    assert v.validate(ds).passed is True
    ds2 = FakeDS(ExposureTime="10")
    assert v.validate(ds2).passed is False


def test_protocol_name_check():
    ds = FakeDS(ProtocolName="Axial Brain")
    v = DICOMProtocolNameCheck(allowed=["Axial Brain", "Sagittal Spine"])
    assert v.validate(ds).passed is True
    ds2 = FakeDS(ProtocolName="Coronal Chest")
    assert v.validate(ds2).passed is False


def test_patient_position_check():
    ds = FakeDS(PatientPosition="HFS")
    v = DICOMPatientPositionCheck()
    assert v.validate(ds).passed is True
    ds2 = FakeDS(PatientPosition="HFP")
    assert v.validate(ds2).passed is False
