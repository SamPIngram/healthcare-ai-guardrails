from pathlib import Path
import json

from healthcare_ai_guardrails.config import load_spec
from healthcare_ai_guardrails.runner import GuardrailRunner


def test_load_spec_and_run_tmp_json(tmp_path: Path):
    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text(
        """
input:
  - type: range
    name: in_range
    path: ["x"]
    min: 0
    max: 10
output:
  - type: choice
    name: class_allowed
    path: ["class"]
    allowed: ["A", "B"]
        """,
        encoding="utf-8",
    )

    data_in = tmp_path / "in.json"
    data_in.write_text(json.dumps({"x": 5}), encoding="utf-8")

    spec = load_spec(spec_yaml)
    input_runner = GuardrailRunner(spec.input_validators)
    results = input_runner.run({"x": 5})
    assert all(r.passed for r in results)

    output_runner = GuardrailRunner(spec.output_validators)
    res2 = output_runner.run({"class": "C"})
    assert any(not r.passed for r in res2)
