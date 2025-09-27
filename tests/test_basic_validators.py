from healthcare_ai_guardrails.validators.basic import (
    RangeCheck,
    ChoiceCheck,
    RequiredFieldsCheck,
)


def test_range_check_pass_and_fail():
    rc = RangeCheck(name="age_range", path=["age"], min_value=18, max_value=65)
    assert rc.validate({"age": 30}).passed is True
    assert rc.validate({"age": 10}).passed is False
    assert rc.validate({"age": 70}).passed is False


def test_choice_check():
    cc = ChoiceCheck(name="modality", path=["modality"], allowed=["CT", "MR"])
    assert cc.validate({"modality": "CT"}).passed is True
    assert cc.validate({"modality": "US"}).passed is False


def test_required_fields_check():
    req = RequiredFieldsCheck(name="required", paths=[["a"], ["b", "c"]])
    assert req.validate({"a": 1, "b": {"c": 2}}).passed is True
    assert req.validate({"a": 1, "b": {}}).passed is False
