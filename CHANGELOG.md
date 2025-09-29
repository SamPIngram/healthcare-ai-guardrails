# Changelog

All notable changes to this project will be documented in this file.

## 0.2.0 - 2025-09-29

### Added
- Test DICOM factory helper: `healthcare_ai_guardrails.testing.dicom_factory.create_test_dicom()` for generating synthetic DICOMs in tests.
- YAML spec support for additional DICOM checks: `dicom_sop_class`, `dicom_body_part_examined`, `dicom_photometric_interpretation`, and `dicom_pixel_intensity_range`.
- Documentation improvements for PyPI users (pip install) and CLI quick start.

### Changed
- Release workflow: build-once publishing and improved artifact handling for PyPI release.

### Fixed
- Removed deprecation warnings in DICOM test factory (datetime.utcnow and FileDataset flags).

## 0.1.0
- Initial release to PyPI.
- Core framework with GuardrailRunner and ValidationResult.
- Basic validators: range, choice, required fields.
- DICOM validators: patient age, modality, patient sex, slice thickness, pixel spacing, image orientation, SOP Class UID, BodyPartExamined, photometric interpretation, pixel intensity range.
- JSON Schema validator for structured outputs.
- CLI entrypoint `hc-guardrails`.
- Example YAML spec and tests.
