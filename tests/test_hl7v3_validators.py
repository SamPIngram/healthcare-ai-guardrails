from healthcare_ai_guardrails.validators.hl7v3 import (
    HL7v3XPathExistsCheck,
    HL7v3XPathValueInListCheck,
    HL7v3XPathRegexMatchCheck,
    HL7v3XPathNumericRangeCheck,
)

XML = """
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <id root="2.16.840.1.113883.19.5" extension="12345"/>
  <code code="34133-9" codeSystem="2.16.840.1.113883.6.1"/>
  <component>
    <structuredBody>
      <component>
        <section>
          <entry>
            <observation classCode="OBS" moodCode="EVN">
              <value xsi:type="PQ" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" value="120" unit="mmHg"/>
            </observation>
          </entry>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
"""

NS = {"hl7": "urn:hl7-org:v3"}


def test_hl7v3_xpath_exists():
    r = HL7v3XPathExistsCheck(xpath=".//hl7:id", namespaces=NS).validate(XML)
    assert r.passed


def test_hl7v3_value_in_list():
    r = HL7v3XPathValueInListCheck(
        xpath=".//hl7:code", attr="code", allowed=["34133-9"], namespaces=NS
    ).validate(XML)
    assert r.passed


def test_hl7v3_regex_match():
    r = HL7v3XPathRegexMatchCheck(
        xpath=".//hl7:id", attr="root", pattern=r"[0-9.]+", namespaces=NS
    ).validate(XML)
    assert r.passed


def test_hl7v3_numeric_range():
    r = HL7v3XPathNumericRangeCheck(
        xpath=".//hl7:value", attr="value", min_value=0, max_value=300, namespaces=NS
    ).validate(XML)
    assert r.passed
