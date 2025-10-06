from healthcare_ai_guardrails.validators.hl7 import (
    HL7FieldExistsCheck,
    HL7ValueInListCheck,
    HL7RegexMatchCheck,
    HL7NumericRangeCheck,
)

SAMPLE = """MSH|^~\\&|LAB|RIH|EKG|EKG|198808181126|SECURITY|ADT^A01|MSG00001|P|2.5\rPID|||555-44-4444||EVERYWOMAN^EVE^E||19610615|F|||2222 HOME STREET^^HOMETOWN^OH^44130||(216)123-4567|||M|C|400003403~1129086|111-22-3333\r"""


def test_hl7_field_exists():
    r = HL7FieldExistsCheck(path="MSH-3").validate(SAMPLE)
    assert r.passed


def test_hl7_value_in_list():
    r = HL7ValueInListCheck(path="MSH-9.1", allowed=["ADT"]).validate(SAMPLE)
    assert r.passed


def test_hl7_regex_match():
    r = HL7RegexMatchCheck(path="PID-5.1", pattern=r"[A-Z]+").validate(SAMPLE)
    assert r.passed


def test_hl7_numeric_range_missing():
    r = HL7NumericRangeCheck(path="PID-35", min_value=1, max_value=500).validate(SAMPLE)
    assert not r.passed
