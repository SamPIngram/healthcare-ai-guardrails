# Healthcare AI Guardrails

![PyPI](https://img.shields.io/pypi/v/healthcare-ai-guardrails.svg?logo=pypi&label=PyPI)
![Python Versions](https://img.shields.io/pypi/pyversions/healthcare-ai-guardrails.svg)
![CI](https://github.com/SamPIngram/healthcare-ai-guardrails/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

Lightweight validation guardrails for AI model inputs/outputs in healthcare workflows, with first-class DICOM support.

## Features

- Declarative YAML spec for checks on input and output data
- Built-in validators: numeric ranges, choices, required fields
- **Specific DICOM validators:** patient age, modality, patient sex, patient position, slice thickness, pixel spacing, image orientation, SOP Class UID, BodyPartExamined, PhotometricInterpretation, pixel intensity range, KVP, X-Ray Tube Current, Exposure Time, Protocol Name, and RT Structure Set ROI presence.
- **Generic DICOM validators:** check if a tag's value is in a list, check a tag's value representation (VR), and check if a tag's numeric value is within a range.
- Output structure validation via JSON Schema
- Simple Python API and CLI (`hc-guardrails`)

## Install (users)

Install from PyPI:

```bash
pip install healthcare-ai-guardrails
```

This installs the Python API and a CLI named `hc-guardrails`.

Quick CLI check:

```bash
hc-guardrails examples/spec.example.yaml examples/output.sample.json --mode output
```

If you’re validating DICOM, `pydicom` and `numpy` are already included as dependencies.

## Install (contributors)

Dev install:

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
from healthcare_ai_guardrails import GuardrailRunner
from healthcare_ai_guardrails.validators.dicom import (
    DICOMPatientAgeCheck,
    DICOMModalityCheck,
    DICOMPatientSexCheck,
    DICOMPatientPositionCheck,
    DICOMSliceThicknessCheck,
    DICOMPixelSpacingCheck,
    DICOMImageOrientationCheck,
    DICOMKVPCheck,
    DICOMTubeCurrentCheck,
    DICOMExposureTimeCheck,
    DICOMProtocolNameCheck,
    DICOMRTStructureCheck,
)
from healthcare_ai_guardrails.validators.generic_dicom import (
    DICOMGenericNumericRangeCheck,
    DICOMGenericValueInListCheck,
    DICOMGenericTagTypeCheck,
)
import pydicom

runner = GuardrailRunner(
    [
        # Specific Validators
        DICOMPatientAgeCheck(min_years=18, max_years=90),
        DICOMModalityCheck(allowed_modalities=["CT", "MR"]),
        DICOMPatientSexCheck(allowed=["M", "F", "O"]),
        DICOMPatientPositionCheck(allowed=["HFS", "FFP", "FFS"]),
        DICOMSliceThicknessCheck(min_mm=0.5, max_mm=5),
        DICOMPixelSpacingCheck(min_mm=0.2, max_mm=2.0),
        DICOMImageOrientationCheck(tolerance=1e-3),
        DICOMKVPCheck(min_kvp=80, max_kvp=140),
        DICOMTubeCurrentCheck(min_ma=100, max_ma=500),
        DICOMExposureTimeCheck(min_ms=50, max_ms=200),
        DICOMProtocolNameCheck(allowed=["Axial Brain", "Sagittal Spine"]),
        DICOMRTStructureCheck(required_rois=["Heart", "Lungs"]),
        # Generic Validators
        DICOMGenericValueInListCheck(
            tag="Manufacturer", allowed_values=["SIEMENS", "GE"]
        ),
        DICOMGenericTagTypeCheck(tag="PatientName", expected_vr="PN"),
        DICOMGenericNumericRangeCheck(tag="BeamNumber", min_val=1, max_val=10),
    ]
)

ds = pydicom.dcmread("/path/to/file.dcm")
results = runner.run(ds)
for r in results:
    print(r.name, r.passed, r.message)
```

## YAML Spec schema

Specific DICOM validators:

- `dicom_patient_age_range` – `min_years`, `max_years`, `inclusive` (default: true)
- `dicom_modality_allowed` – `allowed_modalities: ["CT", "MR", ...]`
- `dicom_patient_sex_allowed` – `allowed: ["M", "F", "O"]`
- `dicom_patient_position_allowed` – `allowed: ["HFS", "FFP", "FFS"]`
- `dicom_slice_thickness_range` – `min_mm`, `max_mm`, `inclusive`
- `dicom_pixel_spacing_range` – `min_mm`, `max_mm`, `inclusive`
- `dicom_image_orientation_sane` – `tolerance` (default: 1e-3)
- `dicom_kvp_range` – `min_kvp`, `max_kvp`, `inclusive`
- `dicom_tube_current_range` – `min_ma`, `max_ma`, `inclusive`
- `dicom_exposure_time_range` – `min_ms`, `max_ms`, `inclusive`
- `dicom_protocol_name_allowed` – `allowed: ["Axial Brain", ...]`
- `dicom_rt_structure_present` – `required_rois: ["Heart", ...]`

Generic DICOM validators:

- `dicom_generic_numeric_range` – `tag`, `unit`, `min_val`, `max_val`, `inclusive`
- `dicom_generic_value_in_list` – `tag`, `allowed_values: [...]`
- `dicom_generic_tag_type_check` – `tag`, `expected_vr`

Other generic validators:

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

Supported Python: 3.9–3.13 (tested in CI on Linux; library is pure Python and should work across platforms).

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

- DICOM tags used include: `PatientAge`, `PatientBirthDate`, `StudyDate`, `SeriesDate`, `ContentDate`, `Modality`, `PatientSex`, `PatientPosition`, `SliceThickness`, `PixelSpacing`, `ImageOrientationPatient`, `KVP`, `XRayTubeCurrent`, `ExposureTime`, `ProtocolName`, `SOPClassUID`, `StructureSetROISequence`.
- Age parsing supports Y/M/W/D suffixes (per DICOM), falls back to birthdate computation.
- Validators never raise; failures are returned as `ValidationResult` and can be surfaced as warnings or errors.

## Contributing

PRs welcome. Please add/update tests for new validators or behavior and update `examples/spec.example.yaml` when adding new spec types.

To create DICOMs in tests, use `create_test_dicom` from `healthcare_ai_guardrails.testing.dicom_factory`.

## Releases and changelog

- PyPI: https://pypi.org/project/healthcare-ai-guardrails/
- Changelog: see [CHANGELOG.md](./CHANGELOG.md)

Maintainers (publishing):

- Create a GitHub Release on the `main` branch. The workflow runs tests across Python 3.9–3.13, builds the sdist and universal wheel, and publishes to PyPI.
- Ensure the repository has `PYPI_API_TOKEN` set in Secrets.

## License

MIT
