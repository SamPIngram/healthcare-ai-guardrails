# Healthcare AI Guardrails

Lightweight validation guardrails for AI model inputs/outputs in healthcare workflows, with first-class DICOM support.

## Features

- Declarative YAML spec for checks on input and output data
- Built-in validators: numeric ranges, choices, required fields
- DICOM validators: patient age, modality, patient sex, slice thickness, pixel spacing, image orientation, SOP Class UID, BodyPartExamined, PhotometricInterpretation, pixel intensity range
- Output structure validation via JSON Schema
- Simple Python API and CLI (`hc-guardrails`)

## Install

Dev install (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

With uv (fast Python package manager):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# create and use a virtualenv automatically
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Quick start

Spec (`examples/spec.example.yaml`):

- Input: verify DICOM patient age in [18, 90], modality in {CT, MR}, patient sex in {M,F,O}, slice thickness/pixel spacing ranges, and sane image orientation
- Output: ensure probability ∈ [0, 1] and match a JSON Schema

Run on a DICOM file:

```bash
hc-guardrails examples/spec.example.yaml path/to/file.dcm --mode input
```

Run on a JSON output:

```bash
hc-guardrails examples/spec.example.yaml path/to/output.json --mode output
```

## Python API

```python
from healthcare_ai_guardrails import (
    GuardrailRunner, DICOMPatientAgeCheck, DICOMModalityCheck,
    DICOMPatientSexCheck, DICOMSliceThicknessCheck, DICOMPixelSpacingCheck,
    DICOMImageOrientationCheck
)
import pydicom

runner = GuardrailRunner([
    DICOMPatientAgeCheck(min_years=18, max_years=90),
    DICOMModalityCheck(allowed_modalities=["CT", "MR"]),
    DICOMPatientSexCheck(allowed=["M", "F", "O"]),
    DICOMSliceThicknessCheck(min_mm=0.5, max_mm=5),
    DICOMPixelSpacingCheck(min_mm=0.2, max_mm=2.0),
    DICOMImageOrientationCheck(tolerance=1e-3),
])

ds = pydicom.dcmread("/path/to/file.dcm")
results = runner.run(ds)
for r in results:
    print(r.name, r.passed, r.message)
```

## YAML Spec schema

Input validators:

- `dicom_patient_age` – `min_years`, `max_years`, `inclusive` (default: true)
- `dicom_modality` – `allowed: ["CT", "MR", ...]`
- `dicom_patient_sex` – `allowed: ["M", "F", "O"]`
- `dicom_slice_thickness` – `min_mm`, `max_mm`, `inclusive`
- `dicom_pixel_spacing` – `min_mm`, `max_mm`, `inclusive`
- `dicom_image_orientation` – `tolerance` (default: 1e-3)

Generic validators:

- `range` – `path: [..]`, `min`, `max`, `inclusive`
- `choice` – `path: [..]`, `allowed: [...]`, `case_insensitive`
- `required_fields` – `paths: [[..], [..]]`

Output validators:

- `json_schema` – `schema: {..}` (JSON Schema Draft 2020-12 compatible via `jsonschema`)
- All generic validators above

Example output schema:

```yaml
output:
  - type: json_schema
    name: output_schema
    schema:
      type: object
      required: ["probability", "label"]
      properties:
        probability:
          type: number
          minimum: 0
          maximum: 1
        label:
          type: string
```

## Development

Run tests locally:

```bash
pytest -q
```

With uv:

```bash
uv run pytest -q
```

Lint/type-check (optional suggestions):

```bash
pip install ruff mypy
ruff check .
mypy src
```

Code style:

```bash
pip install black
black .
```

With uv:

```bash
uv pip install black
uv run black .
```

## Notes

- DICOM tags used include: `PatientAge`, `PatientBirthDate`, `StudyDate`, `SeriesDate`, `ContentDate`, `Modality`, `PatientSex`, `SliceThickness`, `PixelSpacing`, `ImageOrientationPatient`.
- Age parsing supports Y/M/W/D suffixes (per DICOM), falls back to birthdate computation.
- Validators never raise; failures are returned as `ValidationResult` and can be surfaced as warnings or errors.

## Contributing

PRs welcome. Please add/update tests for new validators or behavior and update `examples/spec.example.yaml` when adding new spec types.

To create DICOMs in tests, use `create_test_dicom` from `healthcare_ai_guardrails.testing.dicom_factory`.

## License

MIT
