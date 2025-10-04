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

Run
```bash
# Using uv (optional)
uv run python examples/tutorials/autocontouring_tutorial.py

# Or standard Python
python examples/tutorials/autocontouring_tutorial.py
```

Implementation notes
- Uses `DICOMPatientAgeCheck`, `DICOMModalityCheck`, `DICOMProtocolNameCheck`, and `DICOMRTStructureCheck` from the library.
- Loads pydicom’s CT sample; if an RS sample isn’t suitable it creates a minimal RTSTRUCT in-memory with the desired ROI name.
- For more comprehensive output validation, consider adding checks for ROI-Contour pairing, frame-of-reference consistency, and SOP Class constraints.
