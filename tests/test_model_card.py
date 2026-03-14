"""Tests for the RT-AI-Model-Card integration (model_card.py)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from healthcare_ai_guardrails.model_card import (
    _parse_age_range,
    _parse_kvp,
    _parse_modalities,
    _parse_patient_positions,
    _parse_sex,
    _parse_slice_thickness,
    load_model_card,
    model_card_to_spec,
    model_card_to_yaml,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_model_card() -> Dict[str, Any]:
    return {
        "task": "Segmentation",
        "model_basic_information": {"name": "TestModel"},
        "technical_specifications": {
            "model_inputs": ["CT"],
            "model_outputs": ["RTSTRUCT"],
        },
        "training_data": {
            "age": "18-75 years",
            "sex": "Male and Female",
            "inputs_outputs_technical_specifications": [
                {
                    "entry": "CT",
                    "source": "model_inputs",
                    "patient_positioning": "HFS",
                    "scan_acquisition_parameters": "kVp: 120, slice thickness: 1-3mm",
                    "image_resolution": "512x512",
                }
            ],
        },
    }


# ---------------------------------------------------------------------------
# _parse_age_range
# ---------------------------------------------------------------------------

class TestParseAgeRange:
    @pytest.mark.parametrize("text", ["18-75 years", "18–75 years", "18 to 75 years"])
    def test_range_formats(self, text):
        assert _parse_age_range(text) == (18.0, 75.0)

    @pytest.mark.parametrize("text", [">= 18 years", "≥18"])
    def test_lower_bound_only(self, text):
        lo, hi = _parse_age_range(text)
        assert lo == 18.0 and hi is None

    def test_upper_bound_only(self):
        lo, hi = _parse_age_range("< 80 years")
        assert lo is None and hi == 80.0

    def test_decimal_range(self):
        assert _parse_age_range("0.5-2.5 years") == (0.5, 2.5)

    def test_reversed_range_normalised(self):
        assert _parse_age_range("75-18 years") == (18.0, 75.0)

    def test_unparseable_returns_none(self):
        assert _parse_age_range("adults only") == (None, None)
        assert _parse_age_range("") == (None, None)


# ---------------------------------------------------------------------------
# _parse_sex
# ---------------------------------------------------------------------------

class TestParseSex:
    def test_male_and_female_keywords(self):
        assert _parse_sex("Male and Female") == ["M", "F"]

    @pytest.mark.parametrize("text", ["both sexes", "All genders"])
    def test_both_or_all(self, text):
        result = _parse_sex(text)
        assert "M" in result and "F" in result

    def test_shorthand(self):
        assert _parse_sex("M/F") == ["M", "F"]

    @pytest.mark.parametrize("text,code", [("women", "F"), ("men", "M")])
    def test_single_sex(self, text, code):
        assert _parse_sex(text) == [code]

    def test_other_included(self):
        assert set(_parse_sex("Male, Female, and Other")) == {"M", "F", "O"}

    def test_empty(self):
        assert _parse_sex("") == []


# ---------------------------------------------------------------------------
# _parse_modalities
# ---------------------------------------------------------------------------

class TestParseModalities:
    def test_standard_code(self):
        assert _parse_modalities({"technical_specifications": {"model_inputs": ["CT"]}}) == ["CT"]

    @pytest.mark.parametrize("raw,expected", [("MRI", "MR"), ("PET", "PT")])
    def test_normalise_aliases(self, raw, expected):
        assert _parse_modalities({"technical_specifications": {"model_inputs": [raw]}}) == [expected]

    def test_multiple_with_normalisation(self):
        card = {"technical_specifications": {"model_inputs": ["MRI", "CT"]}}
        assert set(_parse_modalities(card)) == {"MR", "CT"}

    def test_empty_list_and_missing_key(self):
        assert _parse_modalities({"technical_specifications": {"model_inputs": []}}) == []
        assert _parse_modalities({}) == []

    def test_deduplication(self):
        card = {"technical_specifications": {"model_inputs": ["CT", "CT"]}}
        assert _parse_modalities(card) == ["CT"]


# ---------------------------------------------------------------------------
# _parse_patient_positions
# ---------------------------------------------------------------------------

class TestParsePatientPositions:
    def test_standard_code(self):
        assert _parse_patient_positions("HFS") == ["HFS"]

    def test_multiple_codes(self):
        assert set(_parse_patient_positions("HFS, FFP")) == {"HFS", "FFP"}

    def test_natural_language(self):
        assert "HFS" in _parse_patient_positions("Head First Supine")

    def test_case_insensitive(self):
        assert "HFS" in _parse_patient_positions("hfs")

    def test_empty_and_unparseable(self):
        assert _parse_patient_positions("") == []
        assert _parse_patient_positions("standard positioning") == []


# ---------------------------------------------------------------------------
# _parse_slice_thickness
# ---------------------------------------------------------------------------

class TestParseSliceThickness:
    @pytest.mark.parametrize("text", ["slice thickness: 1-3mm", "slice thickness 1 to 3 mm"])
    def test_range(self, text):
        assert _parse_slice_thickness(text) == (1.0, 3.0)

    def test_single_value(self):
        assert _parse_slice_thickness("slice thickness: 1.5mm") == (1.5, 1.5)

    def test_mm_slice_suffix(self):
        assert _parse_slice_thickness("3mm slices") == (3.0, 3.0)

    def test_in_mixed_text(self):
        assert _parse_slice_thickness("kVp: 120, slice thickness: 1-3mm, FOV: 500mm") == (1.0, 3.0)

    def test_reversed_normalised(self):
        assert _parse_slice_thickness("slice thickness: 3-1mm") == (1.0, 3.0)

    def test_no_match(self):
        assert _parse_slice_thickness("kVp: 120") == (None, None)
        assert _parse_slice_thickness("") == (None, None)


# ---------------------------------------------------------------------------
# _parse_kvp
# ---------------------------------------------------------------------------

class TestParseKvp:
    @pytest.mark.parametrize("text", ["120 kVp", "kVp: 120"])
    def test_single_value(self, text):
        assert _parse_kvp(text) == (120.0, 120.0)

    @pytest.mark.parametrize("text", ["100-140 kVp", "kVp: 100-140"])
    def test_range(self, text):
        assert _parse_kvp(text) == (100.0, 140.0)

    def test_case_insensitive(self):
        assert _parse_kvp("120 KVP") == (120.0, 120.0)

    def test_in_mixed_text(self):
        assert _parse_kvp("kVp: 120, slice thickness: 1-3mm") == (120.0, 120.0)

    def test_reversed_normalised(self):
        assert _parse_kvp("140-100 kVp") == (100.0, 140.0)

    def test_no_match(self):
        assert _parse_kvp("slice thickness: 1.5mm") == (None, None)
        assert _parse_kvp("") == (None, None)


# ---------------------------------------------------------------------------
# model_card_to_yaml
# ---------------------------------------------------------------------------

class TestModelCardToYaml:
    def test_returns_valid_yaml_with_input_key(self):
        parsed = yaml.safe_load(model_card_to_yaml(_sample_model_card()))
        assert isinstance(parsed, dict)
        assert "input" in parsed

    def test_header_comment_present(self):
        assert model_card_to_yaml(_sample_model_card()).startswith("#")

    def test_modality_validator(self):
        parsed = yaml.safe_load(model_card_to_yaml(_sample_model_card()))
        modality_v = next(v for v in parsed["input"] if v["type"] == "dicom_modality")
        assert "CT" in modality_v["allowed"]
        assert modality_v["severity"] == "error"

    def test_age_validator(self):
        parsed = yaml.safe_load(model_card_to_yaml(_sample_model_card()))
        age_v = next(v for v in parsed["input"] if v["type"] == "dicom_patient_age")
        assert age_v["min_years"] == 18.0
        assert age_v["max_years"] == 75.0
        assert age_v["severity"] == "warning"

    def test_scan_param_validators_present(self):
        parsed = yaml.safe_load(model_card_to_yaml(_sample_model_card()))
        types = {v["type"] for v in parsed["input"]}
        assert {"dicom_patient_sex", "dicom_patient_position", "dicom_slice_thickness", "dicom_kvp"}.issubset(types)

    def test_empty_training_data_produces_minimal_spec(self):
        card: Dict[str, Any] = {"technical_specifications": {"model_inputs": []}, "training_data": {}}
        parsed = yaml.safe_load(model_card_to_yaml(card))
        assert parsed["input"] == []


# ---------------------------------------------------------------------------
# model_card_to_spec
# ---------------------------------------------------------------------------

class TestModelCardToSpec:
    def test_returns_spec_with_validators(self):
        from healthcare_ai_guardrails.config import Spec

        spec = model_card_to_spec(_sample_model_card())
        assert isinstance(spec, Spec)
        assert len(spec.input_validators) > 0
        assert spec.output_validators == []

    def test_validator_details(self):
        from healthcare_ai_guardrails.validators.dicom import DICOMModalityCheck, DICOMPatientAgeCheck

        spec = model_card_to_spec(_sample_model_card())
        modality_v = next(v for v in spec.input_validators if isinstance(v, DICOMModalityCheck))
        assert "CT" in modality_v.allowed_modalities

        age_v = next(v for v in spec.input_validators if isinstance(v, DICOMPatientAgeCheck))
        assert age_v.min_years == 18.0 and age_v.max_years == 75.0


# ---------------------------------------------------------------------------
# load_model_card
# ---------------------------------------------------------------------------

class TestLoadModelCard:
    def test_loads_json_file(self, tmp_path: Path):
        p = tmp_path / "model_card.json"
        p.write_text(json.dumps(_sample_model_card()), encoding="utf-8")
        # accepts both Path and str
        assert load_model_card(p)["task"] == "Segmentation"
        assert isinstance(load_model_card(str(p)), dict)

    def test_raises_on_non_object_json(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            load_model_card(p)
