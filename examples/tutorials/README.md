# Autocontouring Tutorial

This tutorial validates a CT DICOM input and an RT Structure Set (RS) output for an autocontouring model using the library’s built-in DICOM guardrails.

What is validated
- Input CT
  - Patient age between 25 and 65 years
  - Modality is CT
  - Protocol name indicates Head and Neck (exact match against a small allowed list)
- Output RS
  - Contains an ROI named "OralCavity"

Files
- `autocontouring_tutorial.py` – runnable script demonstrating the checks
- `autocontouring_tutorial.yaml` – YAML spec to run the same checks via the CLI

Run
```bash
# Using uv (optional)
uv run python examples/tutorials/autocontouring_tutorial.py

# Or standard Python
python examples/tutorials/autocontouring_tutorial.py

# Run the same checks via the CLI using the YAML spec:
# Input (CT) validations
hc-guardrails examples/tutorials/autocontouring_tutorial.yaml $(python - <<'PY'
import sys
from pydicom.data import get_testdata_file
p = get_testdata_file('CT_small.dcm')
print(p if p else 'path/to/ct.dcm')
PY
) --mode input

# Output (RTSTRUCT) validation. If you have an RS DICOM, use its path; otherwise
# the Python tutorial shows how to construct a minimal RTSTRUCT in-memory.
# Here we show the command form assuming you have `rs.dcm`:
hc-guardrails examples/tutorials/autocontouring_tutorial.yaml rs.dcm --mode output
```

Implementation notes
- Uses `DICOMPatientAgeCheck`, `DICOMModalityCheck`, `DICOMProtocolNameCheck`, and `DICOMRTStructureCheck` from the library.
- Loads pydicom’s CT sample; if an RS sample isn’t suitable it creates a minimal RTSTRUCT in-memory with the desired ROI name.
- For more comprehensive output validation, consider adding checks for ROI-Contour pairing, frame-of-reference consistency, and SOP Class constraints.
