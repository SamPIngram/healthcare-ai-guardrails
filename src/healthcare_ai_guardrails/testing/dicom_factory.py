from __future__ import annotations

from datetime import date
from typing import Tuple, Optional

try:
    import numpy as np
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid
except Exception:  # pragma: no cover - optional for runtime
    np = None
    pydicom = None
    Dataset = object  # type: ignore
    FileDataset = object  # type: ignore


def create_test_dicom(
    shape: Tuple[int, int] = (16, 16),
    pixel_dtype: str = "uint16",
    photometric: str = "MONOCHROME2",
    modality: str = "CT",
    body_part: str = "HEAD",
    patient_sex: str = "M",
    slice_thickness_mm: float = 1.0,
    pixel_spacing_mm: Tuple[float, float] = (0.5, 0.5),
    orientation: Tuple[float, float, float, float, float, float] = (1, 0, 0, 0, 1, 0),
    sop_class_uid: Optional[str] = None,
):
    if pydicom is None or np is None:
        raise RuntimeError("pydicom and numpy required for test DICOM creation")

    rows, cols = shape
    if pixel_dtype == "uint16":
        dtype = np.uint16
        max_val = 4095
    elif pixel_dtype == "int16":
        dtype = np.int16
        max_val = 2047
    else:
        dtype = np.uint8
        max_val = 255

    arr = (np.linspace(0, max_val, rows * cols).reshape(rows, cols)).astype(dtype)

    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = sop_class_uid or generate_uid()
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    ds = FileDataset("", {}, file_meta=file_meta, preamble=b"\0" * 128)
    # Patient/Study/Series basics
    ds.PatientName = "Test^Patient"
    ds.PatientID = "TEST123"
    ds.PatientSex = patient_sex
    ds.PatientBirthDate = "19800101"
    ds.StudyDate = date.today().strftime("%Y%m%d")
    ds.Modality = modality
    ds.BodyPartExamined = body_part
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.PhotometricInterpretation = photometric
    ds.SliceThickness = slice_thickness_mm
    ds.PixelSpacing = [pixel_spacing_mm[0], pixel_spacing_mm[1]]
    ds.ImageOrientationPatient = list(orientation)

    # Image attributes
    ds.SamplesPerPixel = 1
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 16 if dtype in (np.uint16, np.int16) else 8
    ds.BitsStored = ds.BitsAllocated
    ds.HighBit = ds.BitsStored - 1
    ds.PixelRepresentation = 0 if dtype in (np.uint8, np.uint16) else 1
    # Transfer syntax is set in file_meta; avoid deprecated flags on FileDataset
    ds.PixelData = arr.tobytes()

    return ds
