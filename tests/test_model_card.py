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
    _parse_output_modalities,
    _parse_patient_positions,
    _parse_scanner_models,
    _parse_sex,
    _parse_slice_thickness,
    load_model_card,
    model_card_to_extraction_summary,
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
                    "scanner_model": "Siemens SOMATOM Definition AS+, GE Discovery CT750 HD",
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

    @pytest.mark.parametrize("text", ["both sexes", "All genders", "all sexes"])
    def test_both_or_all(self, text):
        result = _parse_sex(text)
        assert "M" in result and "F" in result

    @pytest.mark.parametrize(
        "text,expected", [("all male", ["M"]), ("all female", ["F"])]
    )
    def test_all_plus_single_sex_not_both(self, text, expected):
        """'all male'/'all female' must not be treated as both sexes."""
        assert _parse_sex(text) == expected

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
        assert _parse_modalities(
            {"technical_specifications": {"model_inputs": ["CT"]}}
        ) == ["CT"]

    @pytest.mark.parametrize("raw,expected", [("MRI", "MR"), ("PET", "PT")])
    def test_normalise_aliases(self, raw, expected):
        assert _parse_modalities(
            {"technical_specifications": {"model_inputs": [raw]}}
        ) == [expected]

    def test_multiple_with_normalisation(self):
        card = {"technical_specifications": {"model_inputs": ["MRI", "CT"]}}
        assert set(_parse_modalities(card)) == {"MR", "CT"}

    def test_empty_list_and_missing_key(self):
        assert (
            _parse_modalities({"technical_specifications": {"model_inputs": []}}) == []
        )
        assert _parse_modalities({}) == []

    def test_deduplication(self):
        card = {"technical_specifications": {"model_inputs": ["CT", "CT"]}}
        assert _parse_modalities(card) == ["CT"]

    def test_compound_modality_split(self):
        """PET/CT must produce both PT and CT, not drop CT."""
        card = {"technical_specifications": {"model_inputs": ["PET/CT"]}}
        result = _parse_modalities(card)
        assert set(result) == {"PT", "CT"}

    def test_xray_ct_split(self):
        card = {"technical_specifications": {"model_inputs": ["XRAY/CT"]}}
        result = _parse_modalities(card)
        assert set(result) == {"DX", "CT"}


# ---------------------------------------------------------------------------
# _parse_output_modalities
# ---------------------------------------------------------------------------


class TestParseOutputModalities:
    def test_standard_code(self):
        card = {"technical_specifications": {"model_outputs": ["RTSTRUCT"]}}
        assert _parse_output_modalities(card) == ["RTSTRUCT"]

    def test_normalise_aliases(self):
        card = {"technical_specifications": {"model_outputs": ["MRI"]}}
        assert _parse_output_modalities(card) == ["MR"]

    def test_empty_list(self):
        card = {"technical_specifications": {"model_outputs": []}}
        assert _parse_output_modalities(card) == []

    def test_missing_key(self):
        assert _parse_output_modalities({}) == []


# ---------------------------------------------------------------------------
# _parse_scanner_models
# ---------------------------------------------------------------------------


class TestParseScannerModels:
    def test_single_model(self):
        assert _parse_scanner_models("Siemens SOMATOM Definition AS+") == [
            "Siemens SOMATOM Definition AS+"
        ]

    def test_comma_separated(self):
        result = _parse_scanner_models(
            "Siemens SOMATOM Definition AS+, GE Discovery CT750 HD"
        )
        assert result == ["Siemens SOMATOM Definition AS+", "GE Discovery CT750 HD"]

    def test_empty(self):
        assert _parse_scanner_models("") == []
        assert _parse_scanner_models("   ") == []


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
    @pytest.mark.parametrize(
        "text", ["slice thickness: 1-3mm", "slice thickness 1 to 3 mm"]
    )
    def test_range(self, text):
        assert _parse_slice_thickness(text) == (1.0, 3.0)

    def test_single_value(self):
        assert _parse_slice_thickness("slice thickness: 1.5mm") == (1.5, 1.5)

    def test_mm_slice_suffix(self):
        assert _parse_slice_thickness("3mm slices") == (3.0, 3.0)

    def test_in_mixed_text(self):
        assert _parse_slice_thickness(
            "kVp: 120, slice thickness: 1-3mm, FOV: 500mm"
        ) == (1.0, 3.0)

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
        assert {
            "dicom_patient_sex",
            "dicom_patient_position",
            "dicom_slice_thickness",
            "dicom_kvp",
        }.issubset(types)

    def test_output_modality_validator_in_output_section(self):
        parsed = yaml.safe_load(model_card_to_yaml(_sample_model_card()))
        assert "output" in parsed
        assert len(parsed["output"]) == 1
        assert parsed["output"][0]["type"] == "dicom_modality"
        assert "RTSTRUCT" in parsed["output"][0]["allowed"]

    def test_scanner_model_validator_present(self):
        parsed = yaml.safe_load(model_card_to_yaml(_sample_model_card()))
        scanner_v = next(
            (v for v in parsed["input"] if v["type"] == "dicom_generic_value_in_list"),
            None,
        )
        assert scanner_v is not None
        assert scanner_v["tag"] == "ManufacturerModelName"
        assert "Siemens SOMATOM Definition AS+" in scanner_v["allowed_values"]

    def test_skipped_fields_appear_in_comment(self):
        card: Dict[str, Any] = {
            "technical_specifications": {"model_inputs": []},
            "training_data": {},
        }
        raw = model_card_to_yaml(card)
        assert "Fields not extracted" in raw
        assert "modalities" in raw

    def test_empty_training_data_produces_minimal_spec(self):
        card: Dict[str, Any] = {
            "technical_specifications": {"model_inputs": []},
            "training_data": {},
        }
        parsed = yaml.safe_load(model_card_to_yaml(card))
        assert parsed["input"] == []

    def test_newline_in_model_name_does_not_break_yaml(self):
        """A newline in the model name must not create a multi-line YAML comment."""
        card: Dict[str, Any] = {
            "model_basic_information": {"name": "Evil\nModel"},
            "technical_specifications": {"model_inputs": []},
            "training_data": {},
        }
        raw = model_card_to_yaml(card)
        # Every line that starts with "#" is still a comment
        for line in raw.splitlines():
            if line.startswith("#"):
                assert "\n" not in line
        # Must still parse as valid YAML
        assert yaml.safe_load(raw) is not None


# ---------------------------------------------------------------------------
# model_card_to_spec
# ---------------------------------------------------------------------------


class TestModelCardToSpec:
    def test_returns_spec_with_validators(self):
        from healthcare_ai_guardrails.config import Spec

        spec = model_card_to_spec(_sample_model_card())
        assert isinstance(spec, Spec)
        assert len(spec.input_validators) > 0
        # RTSTRUCT in model_outputs → output modality validator
        assert len(spec.output_validators) == 1

    def test_validator_details(self):
        from healthcare_ai_guardrails.validators.dicom import (
            DICOMModalityCheck,
            DICOMPatientAgeCheck,
        )

        spec = model_card_to_spec(_sample_model_card())
        modality_v = next(
            v for v in spec.input_validators if isinstance(v, DICOMModalityCheck)
        )
        assert "CT" in modality_v.allowed_modalities

        age_v = next(
            v for v in spec.input_validators if isinstance(v, DICOMPatientAgeCheck)
        )
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


# ---------------------------------------------------------------------------
# model_card_to_extraction_summary
# ---------------------------------------------------------------------------


class TestModelCardToExtractionSummary:
    def test_extracted_fields_from_full_card(self):
        summary = model_card_to_extraction_summary(_sample_model_card())
        extracted = summary["extracted"]
        assert extracted["modalities"] == ["CT"]
        assert extracted["age_range"] == [18.0, 75.0]
        assert set(extracted["sex"]) == {"M", "F"}
        assert "HFS" in extracted["patient_positions"]
        assert extracted["slice_thickness_mm"] == [1.0, 3.0]
        assert extracted["kvp"] == [120.0, 120.0]
        assert extracted["output_modalities"] == ["RTSTRUCT"]
        assert "Siemens SOMATOM Definition AS+" in extracted["scanner_models"]

    def test_skipped_fields_empty_card(self):
        card: Dict[str, Any] = {
            "technical_specifications": {"model_inputs": []},
            "training_data": {},
        }
        summary = model_card_to_extraction_summary(card)
        assert "modalities" in summary["skipped_fields"]
        assert "age" in summary["skipped_fields"]

    def test_return_structure(self):
        summary = model_card_to_extraction_summary(_sample_model_card())
        assert "extracted" in summary
        assert "skipped_fields" in summary
        assert isinstance(summary["extracted"], dict)
        assert isinstance(summary["skipped_fields"], list)


# ---------------------------------------------------------------------------
# Integration: load → generate spec → verify validators
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_load_generate_spec_roundtrip(self, tmp_path: Path):
        """Full pipeline: save JSON file, load it, generate Spec, verify validators."""
        p = tmp_path / "card.json"
        p.write_text(json.dumps(_sample_model_card()), encoding="utf-8")
        card = load_model_card(p)
        spec = model_card_to_spec(card)
        # modality + age + sex + position + slice thickness + kvp + scanner model
        assert len(spec.input_validators) >= 4
        # RTSTRUCT in model_outputs → output modality validator
        assert len(spec.output_validators) == 1

    def test_load_generate_yaml_is_valid_yaml(self, tmp_path: Path):
        p = tmp_path / "card.json"
        p.write_text(json.dumps(_sample_model_card()), encoding="utf-8")
        card = load_model_card(p)
        raw_yaml = model_card_to_yaml(card)
        parsed = yaml.safe_load(raw_yaml)
        assert isinstance(parsed, dict)
        assert "input" in parsed
        assert "output" in parsed
        assert len(parsed["input"]) >= 4
        assert len(parsed["output"]) == 1
