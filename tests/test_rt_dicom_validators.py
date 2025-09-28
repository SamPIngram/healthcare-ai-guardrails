from healthcare_ai_guardrails.validators.dicom import DICOMRTStructureCheck


class FakeROI:
    def __init__(self, name):
        self.ROIName = name


class FakeDS(dict):
    def __getattr__(self, item):
        return self.get(item)


def test_rt_structure_check_valid():
    ds = FakeDS(
        SOPClassUID="1.2.840.10008.5.1.4.1.1.481.3",
        Modality="RTSTRUCT",
        StructureSetROISequence=[
            FakeROI("Heart"),
            FakeROI("Lungs"),
        ],
    )
    v = DICOMRTStructureCheck(required_rois=["Heart", "Lungs"])
    result = v.validate(ds)
    assert result.passed is True
    assert "present_rois" in result.context
    assert set(result.context["present_rois"]) == {"Heart", "Lungs"}


def test_rt_structure_check_missing_roi():
    ds = FakeDS(
        SOPClassUID="1.2.840.10008.5.1.4.1.1.481.3",
        Modality="RTSTRUCT",
        StructureSetROISequence=[
            FakeROI("Heart"),
        ],
    )
    v = DICOMRTStructureCheck(required_rois=["Heart", "Lungs"])
    result = v.validate(ds)
    assert result.passed is False
    assert "Missing ROIs: Lungs" in result.message
    assert "missing_rois" in result.context
    assert result.context["missing_rois"] == ["Lungs"]


def test_rt_structure_check_not_rtstruct_sop_class():
    ds = FakeDS(
        SOPClassUID="1.2.840.10008.5.1.4.1.1.2",  # CT Image Storage
        Modality="CT",
    )
    v = DICOMRTStructureCheck(required_rois=["Heart"])
    result = v.validate(ds)
    assert result.passed is False
    assert "Not an RT Structure Set" in result.message


def test_rt_structure_check_not_rtstruct_modality():
    ds = FakeDS(
        SOPClassUID="1.2.840.10008.5.1.4.1.1.481.3",
        Modality="CT",
    )
    v = DICOMRTStructureCheck(required_rois=["Heart"])
    result = v.validate(ds)
    assert result.passed is False
    assert "Modality is not RTSTRUCT" in result.message


def test_rt_structure_check_no_roi_sequence():
    ds = FakeDS(
        SOPClassUID="1.2.840.10008.5.1.4.1.1.481.3",
        Modality="RTSTRUCT",
    )
    v = DICOMRTStructureCheck(required_rois=["Heart"])
    result = v.validate(ds)
    assert result.passed is False
    assert "StructureSetROISequence not found" in result.message


def test_rt_structure_check_no_required_rois():
    ds = FakeDS(
        SOPClassUID="1.2.840.10008.5.1.4.1.1.481.3",
        Modality="RTSTRUCT",
        StructureSetROISequence=[
            FakeROI("Heart"),
        ],
    )
    v = DICOMRTStructureCheck(required_rois=None)
    result = v.validate(ds)
    assert result.passed is True
    assert "No required ROIs specified" in result.message
