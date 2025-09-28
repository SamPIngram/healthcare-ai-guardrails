from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    import pydicom
except Exception:  # optional import at runtime; errors handled in validate
    pydicom = None

from ..runner import ValidationResult, Severity
from .generic_dicom import (
    _get,
    DICOMGenericNumericRangeCheck,
    DICOMGenericValueInListCheck,
)


def _to_age_years(ds: Any) -> float | None:
    # Prefer PatientAge (0010,1010) if present: format like '034Y'
    age_val = _get(ds, "PatientAge")
    if age_val:
        s = str(age_val).strip()
        try:
            if s.endswith("Y"):
                return float(s[:-1])
            if s.endswith("M"):
                return float(s[:-1]) / 12.0
            if s.endswith("W"):
                return float(s[:-1]) / 52.0
            if s.endswith("D"):
                return float(s[:-1]) / 365.0
            # fallthrough treat as years
            return float(s)
        except Exception:
            pass
    # Fallback: from PatientBirthDate (YYYYMMDD) and StudyDate
    birth = _get(ds, "PatientBirthDate")
    study = _get(ds, "StudyDate") or _get(ds, "SeriesDate") or _get(ds, "ContentDate")
    fmt = "%Y%m%d"
    try:
        if birth:
            b = datetime.strptime(str(birth), fmt)
            ref_date = (
                datetime.strptime(str(study), fmt) if study else datetime.utcnow()
            )
            days = (ref_date - b).days
            return days / 365.25
    except Exception:
        return None
    return None


@dataclass
class DICOMPatientAgeCheck:
    name: str = "dicom_patient_age_range"
    min_years: float | None = None
    max_years: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = "Ensure patient age at study falls within training bounds"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        age_years = _to_age_years(ds)
        if age_years is None:
            return ValidationResult(
                self.name,
                False,
                message="Unable to determine patient age",
                severity=self.severity,
            )
        passed = True
        msgs = []
        if self.min_years is not None:
            if self.inclusive and age_years < self.min_years:
                passed = False
                msgs.append(f"{age_years:.2f} < min {self.min_years}")
            if not self.inclusive and age_years <= self.min_years:
                passed = False
                msgs.append(f"{age_years:.2f} <= min {self.min_years}")
        if self.max_years is not None:
            if self.inclusive and age_years > self.max_years:
                passed = False
                msgs.append(f"{age_years:.2f} > max {self.max_years}")
            if not self.inclusive and age_years >= self.max_years:
                passed = False
                msgs.append(f"{age_years:.2f} >= max {self.max_years}")
        message = "; ".join(msgs)
        return ValidationResult(
            self.name,
            passed,
            message=message,
            severity=self.severity,
            context={"age_years": age_years},
        )


@dataclass
class DICOMModalityCheck:
    allowed_modalities: list[str]
    name: str = "dicom_modality_allowed"
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM modality matches expected set"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericValueInListCheck(
            tag="Modality",
            allowed_values=self.allowed_modalities,
            name=self.name,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMPatientPositionCheck:
    allowed: list[str]
    name: str = "dicom_patient_position_allowed"
    severity: Severity = Severity.WARNING
    description: str = "Ensure PatientPosition is one of the allowed values"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericValueInListCheck(
            tag="PatientPosition",
            allowed_values=self.allowed,
            name=self.name,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMPatientSexCheck:
    name: str = "dicom_patient_sex_allowed"
    allowed: list[str] | None = None
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM PatientSex matches allowed set"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericValueInListCheck(
            tag="PatientSex",
            allowed_values=self.allowed or ["M", "F", "O"],
            name=self.name,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMSliceThicknessCheck:
    name: str = "dicom_slice_thickness_range"
    min_mm: float | None = None
    max_mm: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM SliceThickness is within expected range (mm)"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericNumericRangeCheck(
            tag="SliceThickness",
            unit="mm",
            min_val=self.min_mm,
            max_val=self.max_mm,
            inclusive=self.inclusive,
            name=self.name,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMPixelSpacingCheck:
    name: str = "dicom_pixel_spacing_range"
    min_mm: float | None = None
    max_mm: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = (
        "Ensure each DICOM PixelSpacing value is within expected range (mm)"
    )

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        val = _get(ds, "PixelSpacing")  # typically [row, col]
        if val is None:
            return ValidationResult(
                self.name, False, message="PixelSpacing missing", severity=self.severity
            )
        try:
            values = [
                float(x) for x in (list(val) if hasattr(val, "__iter__") else [val])
            ]
        except Exception:
            return ValidationResult(
                self.name,
                False,
                message=f"PixelSpacing not numeric: {val}",
                severity=self.severity,
            )
        msgs = []
        passed = True
        for v in values:
            if self.min_mm is not None:
                if self.inclusive and v < self.min_mm:
                    passed = False
                    msgs.append(f"{v} < min {self.min_mm} mm")
                if not self.inclusive and v <= self.min_mm:
                    passed = False
                    msgs.append(f"{v} <= min {self.min_mm} mm")
            if self.max_mm is not None:
                if self.inclusive and v > self.max_mm:
                    passed = False
                    msgs.append(f"{v} > max {self.max_mm} mm")
                if not self.inclusive and v >= self.max_mm:
                    passed = False
                    msgs.append(f"{v} >= max {self.max_mm} mm")
        return ValidationResult(
            self.name,
            passed,
            message="; ".join(msgs),
            severity=self.severity,
            context={"pixel_spacing_mm": values},
        )


@dataclass
class DICOMImageOrientationCheck:
    name: str = "dicom_image_orientation_sane"
    tolerance: float = 1e-3
    severity: Severity = Severity.WARNING
    description: str = (
        "Ensure ImageOrientationPatient has orthonormal direction cosines"
    )

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        ori = _get(ds, "ImageOrientationPatient")
        if not ori or len(ori) != 6:
            return ValidationResult(
                self.name,
                False,
                message="ImageOrientationPatient missing or invalid",
                severity=self.severity,
            )
        try:
            import math

            vx = [float(ori[0]), float(ori[1]), float(ori[2])]
            vy = [float(ori[3]), float(ori[4]), float(ori[5])]

            def dot(a, b):
                return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

            def norm(a):
                return math.sqrt(dot(a, a))

            nx, ny = norm(vx), norm(vy)
            d = dot(vx, vy)
            conds = []
            conds.append(abs(nx - 1) <= self.tolerance)
            conds.append(abs(ny - 1) <= self.tolerance)
            conds.append(abs(d) <= self.tolerance)  # orthogonal
            passed = all(conds)
            msg_parts = []
            if not conds[0]:
                msg_parts.append(f"|vx|={nx:.4f} not ~1")
            if not conds[1]:
                msg_parts.append(f"|vy|={ny:.4f} not ~1")
            if not conds[2]:
                msg_parts.append(f"dot(vx,vy)={d:.4f} not ~0")
            return ValidationResult(
                self.name,
                passed,
                message="; ".join(msg_parts),
                severity=self.severity,
                context={"vx": vx, "vy": vy, "nx": nx, "ny": ny, "dot": d},
            )
        except Exception as exc:
            return ValidationResult(
                self.name,
                False,
                message=f"Failed to evaluate orientation: {exc}",
                severity=self.severity,
            )


@dataclass
class DICOMSOPClassCheck:
    allowed_uids: list[str]
    name: str = "dicom_sop_class_allowed"
    severity: Severity = Severity.WARNING
    description: str = "Ensure SOPClassUID is one of the allowed UIDs"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericValueInListCheck(
            name=self.name,
            tag="SOPClassUID",
            allowed_values=self.allowed_uids,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMBodyPartExaminedCheck:
    allowed: list[str]
    name: str = "dicom_body_part_examined_allowed"
    severity: Severity = Severity.WARNING
    description: str = "Ensure BodyPartExamined is allowed"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericValueInListCheck(
            name=self.name,
            tag="BodyPartExamined",
            allowed_values=self.allowed,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMPhotometricInterpretationCheck:
    allowed: list[str]
    name: str = "dicom_photometric_interpretation_allowed"
    severity: Severity = Severity.WARNING
    description: str = "Ensure PhotometricInterpretation is allowed"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericValueInListCheck(
            name=self.name,
            tag="PhotometricInterpretation",
            allowed_values=self.allowed,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMPixelIntensityRangeCheck:
    name: str = "dicom_pixel_intensity_range"
    min_value: float | None = None
    max_value: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = "Ensure pixel intensity values fall within expected range"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        try:
            arr = ds.pixel_array  # type: ignore[attr-defined]
        except Exception as exc:
            return ValidationResult(
                self.name,
                False,
                message=f"Cannot obtain pixel_array: {exc}",
                severity=self.severity,
            )
        try:
            vmin = float(arr.min())
            vmax = float(arr.max())
        except Exception as exc:
            return ValidationResult(
                self.name,
                False,
                message=f"Cannot compute min/max: {exc}",
                severity=self.severity,
            )
        passed = True
        msgs = []
        if self.min_value is not None:
            if self.inclusive and vmin < self.min_value:
                passed = False
                msgs.append(f"min {vmin} < expected min {self.min_value}")
            if not self.inclusive and vmin <= self.min_value:
                passed = False
                msgs.append(f"min {vmin} <= expected min {self.min_value}")
        if self.max_value is not None:
            if self.inclusive and vmax > self.max_value:
                passed = False
                msgs.append(f"max {vmax} > expected max {self.max_value}")
            if not self.inclusive and vmax >= self.max_value:
                passed = False
                msgs.append(f"max {vmax} >= expected max {self.max_value}")
        return ValidationResult(
            self.name,
            passed,
            message="; ".join(msgs),
            severity=self.severity,
            context={"min": vmin, "max": vmax},
        )


@dataclass
class DICOMKVPCheck:
    name: str = "dicom_kvp_range"
    min_kvp: float | None = None
    max_kvp: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM KVP is within expected range"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericNumericRangeCheck(
            tag="KVP",
            name=self.name,
            unit="kVp",
            min_val=self.min_kvp,
            max_val=self.max_kvp,
            inclusive=self.inclusive,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMTubeCurrentCheck:
    name: str = "dicom_tube_current_range"
    min_ma: float | None = None
    max_ma: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM XRayTubeCurrent is within expected range (mA)"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericNumericRangeCheck(
            tag="XRayTubeCurrent",
            name=self.name,
            unit="mA",
            min_val=self.min_ma,
            max_val=self.max_ma,
            inclusive=self.inclusive,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMExposureTimeCheck:
    name: str = "dicom_exposure_time_range"
    min_ms: float | None = None
    max_ms: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM ExposureTime is within expected range (ms)"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericNumericRangeCheck(
            tag="ExposureTime",
            name=self.name,
            unit="ms",
            min_val=self.min_ms,
            max_val=self.max_ms,
            inclusive=self.inclusive,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMProtocolNameCheck:
    allowed: list[str]
    name: str = "dicom_protocol_name_allowed"
    severity: Severity = Severity.WARNING
    description: str = "Ensure ProtocolName is allowed"

    def validate(self, ds: Any) -> ValidationResult:
        checker = DICOMGenericValueInListCheck(
            name=self.name,
            tag="ProtocolName",
            allowed_values=self.allowed,
            severity=self.severity,
        )
        return checker.validate(ds)


@dataclass
class DICOMRTStructureCheck:
    required_rois: list[str]
    name: str = "dicom_rt_structure_present"
    severity: Severity = Severity.WARNING
    description: str = "Ensure required ROIs are present in the RT Structure Set"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )

        # Check if it's an RT Structure Set
        sop_class_uid = _get(ds, "SOPClassUID")
        if sop_class_uid != "1.2.840.10008.5.1.4.1.1.481.3":
            return ValidationResult(
                self.name,
                False,
                message=f"Not an RT Structure Set (SOPClassUID is {sop_class_uid})",
                severity=self.severity,
            )

        modality = _get(ds, "Modality")
        if modality != "RTSTRUCT":
            return ValidationResult(
                self.name,
                False,
                message=f"Modality is not RTSTRUCT, but {modality}",
                severity=self.severity,
            )

        roi_sequence = _get(ds, "StructureSetROISequence")
        if not roi_sequence:
            return ValidationResult(
                self.name,
                False,
                message="StructureSetROISequence not found.",
                severity=self.severity,
            )

        present_rois = {
            item.ROIName for item in roi_sequence if hasattr(item, "ROIName")
        }
        missing_rois = [roi for roi in self.required_rois if roi not in present_rois]

        if not missing_rois:
            return ValidationResult(
                self.name,
                True,
                severity=self.severity,
                context={"present_rois": list(present_rois)},
            )
        else:
            return ValidationResult(
                self.name,
                False,
                message=f"Missing ROIs: {', '.join(missing_rois)}",
                severity=self.severity,
                context={
                    "present_rois": list(present_rois),
                    "missing_rois": missing_rois,
                },
            )
