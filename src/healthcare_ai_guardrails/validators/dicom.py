from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    import pydicom
except Exception:  # optional import at runtime; errors handled in validate
    pydicom = None

from ..runner import ValidationResult, Severity


def _get(ds: Any, tag: str) -> Any:
    if ds is None:
        return None
    if hasattr(ds, "get"):
        try:
            return ds.get(tag)
        except Exception:
            # pydicom Dataset has attribute access too
            return getattr(ds, tag, None)
    return getattr(ds, tag, None)


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
    name: str = "dicom_modality_allowed"
    allowed_modalities: list[str] = None  # e.g., ["CT", "MR", "DX"]
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM modality matches expected set"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        modality = _get(ds, "Modality")
        if modality is None:
            return ValidationResult(
                self.name, False, message="Modality missing", severity=self.severity
            )
        allowed = self.allowed_modalities or []
        passed = str(modality) in allowed if allowed else True
        msg = "" if passed else f"Modality {modality!r} not in {allowed}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class DICOMPatientSexCheck:
    name: str = "dicom_patient_sex_allowed"
    allowed: list[str] | None = None  # e.g., ["M", "F", "O"]
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM PatientSex matches allowed set"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        val = _get(ds, "PatientSex")
        if val is None:
            return ValidationResult(
                self.name, False, message="PatientSex missing", severity=self.severity
            )
        allowed = self.allowed or ["M", "F", "O"]
        passed = str(val) in allowed
        msg = "" if passed else f"PatientSex {val!r} not in {allowed}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class DICOMSliceThicknessCheck:
    name: str = "dicom_slice_thickness_range"
    min_mm: float | None = None
    max_mm: float | None = None
    inclusive: bool = True
    severity: Severity = Severity.WARNING
    description: str = "Ensure DICOM SliceThickness is within expected range (mm)"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        val = _get(ds, "SliceThickness")
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message="SliceThickness missing",
                severity=self.severity,
            )
        try:
            v = float(val)
        except Exception:
            return ValidationResult(
                self.name,
                False,
                message=f"SliceThickness not numeric: {val}",
                severity=self.severity,
            )
        passed = True
        msgs = []
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
            context={"slice_thickness_mm": v},
        )


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
    name: str = "dicom_sop_class_allowed"
    allowed_uids: list[str] | None = None
    severity: Severity = Severity.WARNING
    description: str = "Ensure SOPClassUID is one of the allowed UIDs"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        uid = _get(ds, "SOPClassUID")
        if uid is None:
            return ValidationResult(
                self.name, False, message="SOPClassUID missing", severity=self.severity
            )
        allowed = self.allowed_uids or []
        passed = str(uid) in allowed if allowed else True
        msg = "" if passed else f"SOPClassUID {uid!r} not in {allowed}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class DICOMBodyPartExaminedCheck:
    name: str = "dicom_body_part_examined_allowed"
    allowed: list[str] | None = None
    severity: Severity = Severity.WARNING
    description: str = "Ensure BodyPartExamined is allowed"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        val = _get(ds, "BodyPartExamined")
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message="BodyPartExamined missing",
                severity=self.severity,
            )
        allowed = self.allowed or []
        passed = (str(val) in allowed) if allowed else True
        msg = "" if passed else f"BodyPartExamined {val!r} not in {allowed}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


@dataclass
class DICOMPhotometricInterpretationCheck:
    name: str = "dicom_photometric_interpretation_allowed"
    allowed: list[str] | None = None  # e.g., ["MONOCHROME2", "RGB"]
    severity: Severity = Severity.WARNING
    description: str = "Ensure PhotometricInterpretation is allowed"

    def validate(self, ds: Any) -> ValidationResult:
        if pydicom is None:
            return ValidationResult(
                self.name,
                False,
                message="pydicom not installed",
                severity=Severity.ERROR,
            )
        val = _get(ds, "PhotometricInterpretation")
        if val is None:
            return ValidationResult(
                self.name,
                False,
                message="PhotometricInterpretation missing",
                severity=self.severity,
            )
        allowed = self.allowed or []
        passed = (str(val) in allowed) if allowed else True
        msg = "" if passed else f"PhotometricInterpretation {val!r} not in {allowed}"
        return ValidationResult(self.name, passed, message=msg, severity=self.severity)


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
