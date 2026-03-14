## v0.5.0 - 2026-03-14

### Added
- **RT-AI-Model-Card integration**: `load_model_card`, `model_card_to_yaml`, `model_card_to_spec`, and `model_card_to_extraction_summary` parse an exported model card JSON and auto-generate a guardrail YAML spec covering modality, patient age, sex, patient position, slice thickness, and kVp.
- `--from-model-card` and `--generate-spec` CLI flags for model-card-driven validation workflows (no manual YAML authoring required).
- `generate_spec_from_model_card` MCP tool for AI-agent workflows.
- Sample model card JSON at `examples/model_card.sample.json`.

## v0.4.0 - 2026-02-25

## What's Changed
* improve package adoption: fix deps, add typing, coverage, and contributor docs by @SamPIngram in https://github.com/SamPIngram/healthcare-ai-guardrails/pull/5


**Full Changelog**: https://github.com/SamPIngram/healthcare-ai-guardrails/compare/v0.3.0-alpha...v0.4.0

## v0.0.5 - 2026-02-25

**Full Changelog**: https://github.com/SamPIngram/healthcare-ai-guardrails/compare/v0.0.4-beta...v0.0.5

## v0.0.4-beta - 2026-02-25

## What's Changed
* improve package adoption: fix deps, add typing, coverage, and contributor docs by @SamPIngram in https://github.com/SamPIngram/healthcare-ai-guardrails/pull/5


**Full Changelog**: https://github.com/SamPIngram/healthcare-ai-guardrails/compare/v0.3.0-alpha...v0.0.4-beta

## v0.3.0-alpha - 2025-10-06

**Full Changelog**: https://github.com/SamPIngram/healthcare-ai-guardrails/compare/v0.2.0-alpha...v0.3.0-alpha

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
