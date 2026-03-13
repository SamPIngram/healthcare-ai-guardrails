from __future__ import annotations

import argparse
from pathlib import Path

from ._io import load_data_from_path
from .config import load_spec
from .runner import GuardrailRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Healthcare AI Guardrails")
    parser.add_argument("spec", type=str, help="Path to YAML spec file")
    parser.add_argument(
        "data", type=str, help="Path to input/output data (DICOM .dcm or JSON)"
    )
    parser.add_argument(
        "--mode", choices=["input", "output"], default="input", help="Which set to run"
    )
    args = parser.parse_args(argv)

    spec = load_spec(args.spec)
    try:
        data = load_data_from_path(Path(args.data))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    validators = (
        spec.input_validators if args.mode == "input" else spec.output_validators
    )
    runner = GuardrailRunner(validators)
    results = runner.run(data)

    any_fail = False
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if not r.passed:
            any_fail = True
        msg = f" - {r.message}" if r.message else ""
        print(f"[{status}] ({r.severity}) {r.name}{msg}")

    return 1 if any_fail else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
