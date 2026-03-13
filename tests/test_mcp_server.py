"""Tests for the MCP server tool functions.

These tests call the underlying tool functions directly (without the MCP
protocol layer) to verify the QA pipeline logic exposed to AI agents.
"""

from __future__ import annotations

import textwrap

from healthcare_ai_guardrails.mcp_server import (
    describe_spec,
    list_validator_types,
    run_guardrails,
    validate_spec,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

SIMPLE_RANGE_SPEC = textwrap.dedent("""
    input:
      - type: range
        name: probability_range
        path: ["probability"]
        min: 0.0
        max: 1.0
    """)

REQUIRED_FIELDS_SPEC = textwrap.dedent("""
    input:
      - type: required_fields
        name: required_check
        paths: [["patient_id"], ["study_date"]]
    output:
      - type: range
        name: confidence_range
        path: ["confidence"]
        min: 0.0
        max: 1.0
    """)

HL7_SPEC = textwrap.dedent("""
    input:
      - type: hl7v2_field_exists
        name: patient_id_present
        path: PID-3
      - type: hl7v2_value_in_list
        name: patient_sex_valid
        path: PID-8
        allowed: [M, F, O, U]
    """)

HL7_MESSAGE = (
    "MSH|^~\\&|SendApp|SendFac|RecvApp|RecvFac|20240101120000||ADT^A01|MSG001|P|2.5\r"
    "PID|1||12345^^^MRN||Doe^John||19800101|M|||123 Main St^^City^ST^12345\r"
)

INVALID_SPEC = textwrap.dedent("""
    input:
      - type: totally_unknown_validator_type
        name: bad_check
    """)


# ---------------------------------------------------------------------------
# run_guardrails tests
# ---------------------------------------------------------------------------


class TestRunGuardrails:
    def test_inline_spec_and_data_pass(self):
        result = run_guardrails(
            spec_yaml=SIMPLE_RANGE_SPEC,
            data_content='{"probability": 0.7}',
            mode="input",
        )
        assert result["summary"]["all_passed"] is True
        assert result["summary"]["total"] == 1
        assert result["summary"]["passed"] == 1
        assert result["results"][0]["name"] == "probability_range"
        assert result["results"][0]["passed"] is True

    def test_inline_spec_and_data_fail(self):
        result = run_guardrails(
            spec_yaml=SIMPLE_RANGE_SPEC,
            data_content='{"probability": 1.5}',
            mode="input",
        )
        assert result["summary"]["all_passed"] is False
        assert result["summary"]["failed"] == 1
        assert result["results"][0]["passed"] is False

    def test_output_mode_uses_output_validators(self):
        result = run_guardrails(
            spec_yaml=REQUIRED_FIELDS_SPEC,
            data_content='{"confidence": 0.9}',
            mode="output",
        )
        assert result["summary"]["total"] == 1
        assert result["results"][0]["name"] == "confidence_range"
        assert result["results"][0]["passed"] is True

    def test_input_mode_uses_input_validators(self):
        result = run_guardrails(
            spec_yaml=REQUIRED_FIELDS_SPEC,
            data_content='{"patient_id": "P001", "study_date": "20240101"}',
            mode="input",
        )
        assert result["summary"]["total"] == 1
        assert result["results"][0]["name"] == "required_check"
        assert result["results"][0]["passed"] is True

    def test_hl7_inline_content(self):
        result = run_guardrails(
            spec_yaml=HL7_SPEC,
            data_content=HL7_MESSAGE,
            mode="input",
        )
        assert result["summary"]["total"] == 2
        assert result["summary"]["passed"] == 2

    def test_spec_from_file(self, tmp_path):
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(SIMPLE_RANGE_SPEC)
        result = run_guardrails(
            spec_path=str(spec_file),
            data_content='{"probability": 0.5}',
            mode="input",
        )
        assert result["summary"]["all_passed"] is True

    def test_data_from_file(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text('{"probability": 0.3}')
        result = run_guardrails(
            spec_yaml=SIMPLE_RANGE_SPEC,
            data_path=str(data_file),
            mode="input",
        )
        assert result["summary"]["all_passed"] is True

    def test_invalid_mode_returns_error(self):
        result = run_guardrails(
            spec_yaml=SIMPLE_RANGE_SPEC,
            data_content='{"probability": 0.5}',
            mode="batch",
        )
        assert "error" in result
        assert "mode" in result["error"].lower()

    def test_missing_data_returns_error(self):
        result = run_guardrails(spec_yaml=SIMPLE_RANGE_SPEC, mode="input")
        assert "error" in result

    def test_bad_spec_returns_error(self):
        result = run_guardrails(
            spec_yaml=INVALID_SPEC,
            data_content='{"x": 1}',
            mode="input",
        )
        assert "error" in result

    def test_result_has_severity_field(self):
        result = run_guardrails(
            spec_yaml=SIMPLE_RANGE_SPEC,
            data_content='{"probability": 0.5}',
            mode="input",
        )
        r = result["results"][0]
        assert "severity" in r
        assert isinstance(r["severity"], str)

    def test_result_has_context_field(self):
        result = run_guardrails(
            spec_yaml=SIMPLE_RANGE_SPEC,
            data_content='{"probability": 0.5}',
            mode="input",
        )
        assert "context" in result["results"][0]


# ---------------------------------------------------------------------------
# list_validator_types tests
# ---------------------------------------------------------------------------


class TestListValidatorTypes:
    def test_returns_validators_list(self):
        result = list_validator_types()
        assert "validators" in result
        assert isinstance(result["validators"], list)
        assert len(result["validators"]) > 0

    def test_returns_categories(self):
        result = list_validator_types()
        assert "categories" in result
        cats = result["categories"]
        assert "generic" in cats
        assert "dicom" in cats
        assert "hl7v2" in cats
        assert "hl7v3" in cats

    def test_all_validators_have_required_keys(self):
        result = list_validator_types()
        for v in result["validators"]:
            assert "type" in v
            assert "description" in v
            assert "required_params" in v
            assert "optional_params" in v
            assert "category" in v

    def test_known_types_are_present(self):
        result = list_validator_types()
        types = {v["type"] for v in result["validators"]}
        assert "range" in types
        assert "dicom_modality" in types
        assert "hl7v2_field_exists" in types
        assert "hl7v3_xpath_exists" in types
        assert "json_schema" in types

    def test_total_matches_list_length(self):
        result = list_validator_types()
        assert result["total"] == len(result["validators"])


# ---------------------------------------------------------------------------
# validate_spec tests
# ---------------------------------------------------------------------------


class TestValidateSpec:
    def test_valid_spec_inline(self):
        result = validate_spec(spec_yaml=SIMPLE_RANGE_SPEC)
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["input_count"] == 1
        assert result["output_count"] == 0

    def test_valid_spec_with_both_sections(self):
        result = validate_spec(spec_yaml=REQUIRED_FIELDS_SPEC)
        assert result["valid"] is True
        assert result["input_count"] == 1
        assert result["output_count"] == 1

    def test_invalid_validator_type(self):
        result = validate_spec(spec_yaml=INVALID_SPEC)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["input_count"] == 0

    def test_invalid_yaml_syntax(self):
        bad_yaml = "input:\n  - type: range\n    name: [unclosed"
        result = validate_spec(spec_yaml=bad_yaml)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_valid_spec_from_file(self, tmp_path):
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(SIMPLE_RANGE_SPEC)
        result = validate_spec(spec_path=str(spec_file))
        assert result["valid"] is True

    def test_empty_spec_is_valid(self):
        result = validate_spec(spec_yaml="input: []\noutput: []")
        assert result["valid"] is True
        assert result["input_count"] == 0
        assert result["output_count"] == 0


# ---------------------------------------------------------------------------
# describe_spec tests
# ---------------------------------------------------------------------------


class TestDescribeSpec:
    def test_returns_input_and_output_sections(self):
        result = describe_spec(spec_yaml=REQUIRED_FIELDS_SPEC)
        assert "input_validators" in result
        assert "output_validators" in result

    def test_input_validator_has_required_fields(self):
        result = describe_spec(spec_yaml=SIMPLE_RANGE_SPEC)
        v = result["input_validators"][0]
        assert "name" in v
        assert "description" in v
        assert "severity" in v
        assert "validator_class" in v

    def test_counts_match(self):
        result = describe_spec(spec_yaml=REQUIRED_FIELDS_SPEC)
        assert result["input_count"] == 1
        assert result["output_count"] == 1
        assert len(result["input_validators"]) == 1
        assert len(result["output_validators"]) == 1

    def test_validator_name_is_correct(self):
        result = describe_spec(spec_yaml=SIMPLE_RANGE_SPEC)
        assert result["input_validators"][0]["name"] == "probability_range"

    def test_validator_class_is_set(self):
        result = describe_spec(spec_yaml=SIMPLE_RANGE_SPEC)
        assert result["input_validators"][0]["validator_class"] == "RangeCheck"

    def test_error_on_bad_spec(self):
        result = describe_spec(spec_yaml=INVALID_SPEC)
        assert "error" in result
