# Changelog

All notable changes to this project will be documented in this file.

## 0.1.0
- Initial release to PyPI.
- Core framework with GuardrailRunner and ValidationResult.
- Basic validators: range, choice, required fields.
- DICOM validators: patient age, modality, patient sex, slice thickness, pixel spacing, image orientation, SOP Class UID, BodyPartExamined, photometric interpretation, pixel intensity range.
- JSON Schema validator for structured outputs.
- CLI entrypoint `hc-guardrails`.
- Example YAML spec and tests.
