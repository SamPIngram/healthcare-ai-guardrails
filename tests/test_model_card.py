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
    def test_dash_range_years(self):
        assert _parse_age_range("18-75 years") == (18.0, 75.0)

    def test_dash_range_no_unit(self):
        assert _parse_age_range("18-75") == (18.0, 75.0)

    def test_to_range(self):
        assert _parse_age_range("18 to 75 years") == (18.0, 75.0)

    def test_en_dash_range(self):
        assert _parse_age_range("20–80 years") == (20.0, 80.0)

    def test_lower_bound_gte(self):
        lo, hi = _parse_age_range(">= 18 years")
        assert lo == 18.0
        assert hi is None

    def test_lower_bound_unicode_gte(self):
        lo, hi = _parse_age_range("≥18 years")
        assert lo == 18.0
        assert hi is None

    def test_lower_bound_gt(self):
        lo, hi = _parse_age_range("> 18")
        assert lo == 18.0
        assert hi is None

    def test_upper_bound_lt(self):
        lo, hi = _parse_age_range("< 80 years")
        assert lo is None
        assert hi == 80.0

    def test_upper_bound_lte_unicode(self):
        lo, hi = _parse_age_range("≤80")
        assert lo is None
        assert hi == 80.0

    def test_empty_string(self):
        assert _parse_age_range("") == (None, None)

    def test_unparseable(self):
        assert _parse_age_range("adults only") == (None, None)

    def test_decimal(self):
        lo, hi = _parse_age_range("0.5-2.5 years")
        assert lo == 0.5
        assert hi == 2.5

    def test_reversed_range_normalised(self):
        # Parser should always return (min, max) regardless of input order
        lo, hi = _parse_age_range("75-18 years")
        assert lo == 18.0
        assert hi == 75.0


# ---------------------------------------------------------------------------
# _parse_sex
# ---------------------------------------------------------------------------

class TestParseSex:
    def test_male_and_female(self):
        assert _parse_sex("Male and Female") == ["M", "F"]

    def test_both_sexes(self):
        assert _parse_sex("both sexes") == ["M", "F"]

    def test_all_genders(self):
        result = _parse_sex("All genders")
        assert "M" in result and "F" in result

    def test_shorthand_m_f(self):
        assert _parse_sex("M/F") == ["M", "F"]

    def test_shorthand_m_comma_f(self):
        assert _parse_sex("M, F") == ["M", "F"]

    def test_female_only(self):
        assert _parse_sex("Female only") == ["F"]

    def test_male_only(self):
        assert _parse_sex("male patients") == ["M"]

    def test_other_included(self):
        result = _parse_sex("Male, Female, and Other")
        assert set(result) == {"M", "F", "O"}

    def test_empty(self):
        assert _parse_sex("") == []

    def test_women(self):
        assert _parse_sex("women") == ["F"]

    def test_men(self):
        assert _parse_sex("men") == ["M"]


# ---------------------------------------------------------------------------
# _parse_modalities
# ---------------------------------------------------------------------------

class TestParseModalities:
    def test_single_ct(self):
        card = {"technical_specifications": {"model_inputs": ["CT"]}}
        assert _parse_modalities(card) == ["CT"]

    def test_normalise_mri(self):
        card = {"technical_specifications": {"model_inputs": ["MRI"]}}
        assert _parse_modalities(card) == ["MR"]

    def test_normalise_pet(self):
        card = {"technical_specifications": {"model_inputs": ["PET"]}}
        assert _parse_modalities(card) == ["PT"]

    def test_multiple_with_normalisation(self):
        card = {"technical_specifications": {"model_inputs": ["MRI", "CT"]}}
        result = _parse_modalities(card)
        assert set(result) == {"MR", "CT"}

    def test_empty_list(self):
        card = {"technical_specifications": {"model_inputs": []}}
        assert _parse_modalities(card) == []

    def test_missing_key(self):
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
        result = _parse_patient_positions("HFS, FFP")
        assert set(result) == {"HFS", "FFP"}

    def test_natural_language_hfs(self):
        result = _parse_patient_positions("Head First Supine")
        assert "HFS" in result

    def test_natural_language_ffp(self):
        result = _parse_patient_positions("Feet First Prone")
        assert "FFP" in result

    def test_case_insensitive_code(self):
        result = _parse_patient_positions("hfs")
        assert "HFS" in result

    def test_empty(self):
        assert _parse_patient_positions("") == []

    def test_unparseable(self):
        assert _parse_patient_positions("standard positioning") == []


# ---------------------------------------------------------------------------
# _parse_slice_thickness
# ---------------------------------------------------------------------------

class TestParseSliceThickness:
    def test_range_mm(self):
        assert _parse_slice_thickness("slice thickness: 1-3mm") == (1.0, 3.0)

    def test_range_with_to(self):
        assert _parse_slice_thickness("slice thickness 1 to 3 mm") == (1.0, 3.0)

    def test_single_value(self):
        assert _parse_slice_thickness("slice thickness: 1.5mm") == (1.5, 1.5)

    def test_mm_slice_suffix(self):
        assert _parse_slice_thickness("3mm slices") == (3.0, 3.0)

    def test_in_mixed_text(self):
        lo, hi = _parse_slice_thickness("kVp: 120, slice thickness: 1-3mm, FOV: 500mm")
        assert lo == 1.0
        assert hi == 3.0

    def test_no_match(self):
        assert _parse_slice_thickness("kVp: 120") == (None, None)

    def test_empty(self):
        assert _parse_slice_thickness("") == (None, None)

    def test_reversed_normalised(self):
        lo, hi = _parse_slice_thickness("slice thickness: 3-1mm")
        assert lo == 1.0
        assert hi == 3.0


# ---------------------------------------------------------------------------
# _parse_kvp
# ---------------------------------------------------------------------------

class TestParseKvp:
    def test_single_kvp(self):
        assert _parse_kvp("120 kVp") == (120.0, 120.0)

    def test_kvp_colon(self):
        assert _parse_kvp("kVp: 120") == (120.0, 120.0)

    def test_range_kvp(self):
        assert _parse_kvp("100-140 kVp") == (100.0, 140.0)

    def test_kvp_range_colon(self):
        assert _parse_kvp("kVp: 100-140") == (100.0, 140.0)

    def test_in_mixed_text(self):
        lo, hi = _parse_kvp("kVp: 120, slice thickness: 1-3mm")
        assert lo == 120.0
        assert hi == 120.0

    def test_no_match(self):
        assert _parse_kvp("slice thickness: 1.5mm") == (None, None)

    def test_empty(self):
        assert _parse_kvp("") == (None, None)

    def test_case_insensitive(self):
        assert _parse_kvp("120 KVP") == (120.0, 120.0)

    def test_reversed_normalised(self):
        lo, hi = _parse_kvp("140-100 kVp")
        assert lo == 100.0
        assert hi == 140.0


# ---------------------------------------------------------------------------
# model_card_to_yaml
# ---------------------------------------------------------------------------

class TestModelCardToYaml:
    def test_returns_valid_yaml(self):
        card = _sample_model_card()
        result = model_card_to_yaml(card)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)
        assert "input" in parsed

    def test_contains_modality_validator(self):
        card = _sample_model_card()
        result = model_card_to_yaml(card)
        parsed = yaml.safe_load(result)
        types = [v["type"] for v in parsed["input"]]
        assert "dicom_modality" in types

    def test_modality_has_ct(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        modality_v = next(v for v in parsed["input"] if v["type"] == "dicom_modality")
        assert "CT" in modality_v["allowed"]

    def test_age_validator_present(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        types = [v["type"] for v in parsed["input"]]
        assert "dicom_patient_age" in types

    def test_age_validator_bounds(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        age_v = next(v for v in parsed["input"] if v["type"] == "dicom_patient_age")
        assert age_v["min_years"] == 18.0
        assert age_v["max_years"] == 75.0

    def test_sex_validator_present(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        types = [v["type"] for v in parsed["input"]]
        assert "dicom_patient_sex" in types

    def test_patient_position_validator(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        types = [v["type"] for v in parsed["input"]]
        assert "dicom_patient_position" in types

    def test_slice_thickness_validator(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        types = [v["type"] for v in parsed["input"]]
        assert "dicom_slice_thickness" in types

    def test_kvp_validator(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        types = [v["type"] for v in parsed["input"]]
        assert "dicom_kvp" in types

    def test_empty_training_data_produces_minimal_spec(self):
        card: Dict[str, Any] = {
            "technical_specifications": {"model_inputs": []},
            "training_data": {},
        }
        result = model_card_to_yaml(card)
        parsed = yaml.safe_load(result)
        assert parsed["input"] == []

    def test_header_comment_present(self):
        card = _sample_model_card()
        result = model_card_to_yaml(card)
        assert result.startswith("#")

    def test_modality_severity_is_error(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        modality_v = next(v for v in parsed["input"] if v["type"] == "dicom_modality")
        assert modality_v["severity"] == "error"

    def test_age_severity_is_warning(self):
        card = _sample_model_card()
        parsed = yaml.safe_load(model_card_to_yaml(card))
        age_v = next(v for v in parsed["input"] if v["type"] == "dicom_patient_age")
        assert age_v["severity"] == "warning"


# ---------------------------------------------------------------------------
# model_card_to_spec
# ---------------------------------------------------------------------------

class TestModelCardToSpec:
    def test_returns_spec_with_input_validators(self):
        from healthcare_ai_guardrails.config import Spec

        card = _sample_model_card()
        spec = model_card_to_spec(card)
        assert isinstance(spec, Spec)
        assert len(spec.input_validators) > 0

    def test_output_validators_empty(self):
        card = _sample_model_card()
        spec = model_card_to_spec(card)
        assert spec.output_validators == []

    def test_modality_validator_has_ct(self):
        from healthcare_ai_guardrails.validators.dicom import DICOMModalityCheck

        card = _sample_model_card()
        spec = model_card_to_spec(card)
        modality_validators = [v for v in spec.input_validators if isinstance(v, DICOMModalityCheck)]
        assert len(modality_validators) == 1
        assert "CT" in modality_validators[0].allowed_modalities

    def test_age_validator_bounds(self):
        from healthcare_ai_guardrails.validators.dicom import DICOMPatientAgeCheck

        card = _sample_model_card()
        spec = model_card_to_spec(card)
        age_validators = [v for v in spec.input_validators if isinstance(v, DICOMPatientAgeCheck)]
        assert len(age_validators) == 1
        assert age_validators[0].min_years == 18.0
        assert age_validators[0].max_years == 75.0


# ---------------------------------------------------------------------------
# load_model_card
# ---------------------------------------------------------------------------

class TestLoadModelCard:
    def test_loads_json_from_file(self, tmp_path: Path):
        card = _sample_model_card()
        p = tmp_path / "model_card.json"
        p.write_text(json.dumps(card), encoding="utf-8")
        loaded = load_model_card(p)
        assert loaded["task"] == "Segmentation"

    def test_raises_on_non_object_json(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            load_model_card(p)

    def test_accepts_string_path(self, tmp_path: Path):
        card = _sample_model_card()
        p = tmp_path / "model_card.json"
        p.write_text(json.dumps(card), encoding="utf-8")
        loaded = load_model_card(str(p))
        assert isinstance(loaded, dict)
