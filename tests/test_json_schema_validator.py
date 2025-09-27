from healthcare_ai_guardrails.validators.schema import JSONSchemaCheck


def test_json_schema_validator_pass_and_fail():
    schema = {
        "type": "object",
        "required": ["probability", "label"],
        "properties": {
            "probability": {"type": "number", "minimum": 0, "maximum": 1},
            "label": {"type": "string"},
        },
    }
    v = JSONSchemaCheck(schema=schema)
    assert v.validate({"probability": 0.3, "label": "A"}).passed is True
    assert v.validate({"probability": 2.0, "label": "A"}).passed is False
