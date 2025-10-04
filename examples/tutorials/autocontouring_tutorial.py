"""
Tutorial: Guardrails for CT input and RTSTRUCT output (Autocontouring)

Validations
- Input CT:
  - Patient age in [25, 65] years
  - Modality is CT
  - ProtocolName indicates Head and Neck (exact match to one of allowed names)
- Output RS (RT Structure Set):
  - Contains an ROI named "OralCavity"

Run:
  uv run python examples/tutorials/autocontouring_tutorial.py
  # or
  python examples/tutorials/autocontouring_tutorial.py
"""

from __future__ import annotations

from typing import List
import datetime as dt

import pydicom
from pydicom import dcmread
from pydicom.data import get_testdata_file
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence

from healthcare_ai_guardrails import (
    GuardrailRunner,
    DICOMPatientAgeCheck,
    DICOMModalityCheck,
    DICOMProtocolNameCheck,
    DICOMRTStructureCheck,
)
from healthcare_ai_guardrails.runner import Severity


def load_example_ct() -> Dataset:
    """Load pydicom's example CT dataset and normalize tags for the demo."""
    path = get_testdata_file("CT_small.dcm")
    if not path:
        raise RuntimeError("Could not locate pydicom test CT_small.dcm")
    ds = dcmread(path)
    # Normalize for demo
    ds.Modality = "CT"
    ds.PatientAge = "045Y"  # in range [25,65]
    ds.ProtocolName = "Head and Neck"  # exact match to allowed list
    return ds


def contains_roi(rs: Dataset, roi_name: str) -> bool:
    seq = getattr(rs, "StructureSetROISequence", None)
    if not seq:
        return False
    return any(getattr(item, "ROIName", "") == roi_name for item in seq)


def make_mock_rtstruct(roi_names: List[str]) -> Dataset:
    """Create a minimal RT Structure Set with the requested ROI names."""
    ds = Dataset()
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.481.3"  # RT Structure Set Storage
    ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.Modality = "RTSTRUCT"
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.FrameOfReferenceUID = pydicom.uid.generate_uid()
    ds.StructureSetLabel = "AUTO"
    ds.StructureSetDate = dt.date.today().strftime("%Y%m%d")
    ds.StructureSetTime = "120000"

    struct_seq = Sequence()
    for idx, name in enumerate(roi_names, start=1):
        item = Dataset()
        item.ROINumber = idx
        item.ReferencedFrameOfReferenceUID = ds.FrameOfReferenceUID
        item.ROIName = name
        item.ROIDescription = ""
        struct_seq.append(item)
    ds.StructureSetROISequence = struct_seq
    ds.ROIContourSequence = Sequence()
    return ds


def load_or_make_rtstruct(include_oral_cavity: bool = True) -> Dataset:
    path = get_testdata_file("rtstruct.dcm")
    if path:
        rs = dcmread(path, force=True)
        if include_oral_cavity:
            if contains_roi(rs, "OralCavity"):
                return rs
        else:
            # if we want negative example and it already lacks ROI, return as-is
            if not contains_roi(rs, "OralCavity"):
                return rs
    # Create mock RS according to desired presence
    rois = ["OralCavity"] if include_oral_cavity else ["SomeOtherROI"]
    return make_mock_rtstruct(rois)


def main() -> int:
    # Input validation
    input_runner = GuardrailRunner(
        validators=[
            DICOMPatientAgeCheck(min_years=25, max_years=65),
            DICOMModalityCheck(allowed_modalities=["CT"]),
            DICOMProtocolNameCheck(
                allowed=["Head and Neck", "Head and Neck Contrast", "H&N"]
            ),
        ]
    )

    ct = load_example_ct()
    print("Input CT guardrails:")
    for res in input_runner.run(ct):
        msg = res.message
        if not msg:
            # attempt to enrich success messages from context or dataset
            if res.context and "age_years" in res.context:
                msg = f"age={res.context['age_years']:.1f}y within bounds"
            elif res.name == "dicom_modality_allowed":
                msg = f"modality={getattr(ct, 'Modality', '')} allowed"
            elif res.name == "dicom_protocol_name_allowed":
                msg = f"protocol={getattr(ct, 'ProtocolName', '')} allowed"
            else:
                msg = "OK"
        print(
            f" - [{res.severity.name}] {res.name}: {'PASS' if res.passed else 'FAIL'} - {msg}"
        )

    # Output validation
    output_runner = GuardrailRunner(
        validators=[
            DICOMRTStructureCheck(
                required_rois=["OralCavity"],
                severity=Severity.ERROR,
                name="rs_has_oral_cavity",
            )
        ]
    )

    rs_ok = load_or_make_rtstruct(include_oral_cavity=True)
    print("\nOutput RS guardrails (expected PASS):")
    for res in output_runner.run(rs_ok):
        msg = res.message or (
            f"present_rois={res.context.get('present_rois')}"
            if getattr(res, "context", None) and res.context.get("present_rois")
            else "OK"
        )
        print(
            f" - [{res.severity.name}] {res.name}: {'PASS' if res.passed else 'FAIL'} - {msg}"
        )

    rs_bad = load_or_make_rtstruct(include_oral_cavity=False)
    print("\nOutput RS guardrails (expected FAIL):")
    for res in output_runner.run(rs_bad):
        msg = res.message or (
            f"present_rois={res.context.get('present_rois')}"
            if getattr(res, "context", None) and res.context.get("present_rois")
            else "OK"
        )
        print(
            f" - [{res.severity.name}] {res.name}: {'PASS' if res.passed else 'FAIL'} - {msg}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
