from healthcare_ai_guardrails.validators.generic_dicom import (
    DICOMGenericValueInListCheck,
    DICOMGenericTagTypeCheck,
    DICOMGenericNumericRangeCheck,
)


class FakeDS(dict):
    def __getattr__(self, item):
        return self.get(item)


class FakeElement:
    def __init__(self, value, vr):
        self.value = value
        self.VR = vr


def test_generic_numeric_range_check():
    ds = FakeDS(KVP="120")
    v = DICOMGenericNumericRangeCheck(tag="KVP", unit="kVp", min_val=80, max_val=140)
    assert v.validate(ds).passed is True
    ds2 = FakeDS(KVP="70")
    assert v.validate(ds2).passed is False


def test_generic_value_in_list_check():
    ds = FakeDS(Manufacturer="SIEMENS")
    v = DICOMGenericValueInListCheck(
        tag="Manufacturer", allowed_values=["SIEMENS", "GE"]
    )
    assert v.validate(ds).passed is True
    ds2 = FakeDS(Manufacturer="PHILIPS")
    assert v.validate(ds2).passed is False


def test_generic_tag_type_check():
    ds = FakeDS(PatientName=FakeElement("John Doe", "PN"))
    v = DICOMGenericTagTypeCheck(tag="PatientName", expected_vr="PN")
    assert v.validate(ds).passed is True
    ds2 = FakeDS(PatientName=FakeElement("John Doe", "LO"))
    assert v.validate(ds2).passed is False
