from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._io import load_data_from_path
from .config import load_spec
from .runner import GuardrailRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Healthcare AI Guardrails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate using an existing spec file:
  hc-guardrails spec.yaml data.dcm --mode input

  # Generate a spec from an RT-AI-Model-Card JSON and print to stdout:
  hc-guardrails --from-model-card model_card.json --generate-spec

  # Generate a spec and save to file:
  hc-guardrails --from-model-card model_card.json --generate-spec output.yaml

  # Validate data using a model card instead of a spec file:
  hc-guardrails --from-model-card model_card.json data.dcm --mode input
""",
    )
    parser.add_argument(
        "spec",
        type=str,
        nargs="?",
        help="Path to YAML spec file (not required when --from-model-card is used)",
    )
    parser.add_argument(
        "data",
        type=str,
        nargs="?",
        help="Path to input/output data (DICOM .dcm or JSON)",
    )
    parser.add_argument(
        "--mode",
        choices=["input", "output"],
        default="input",
        help="Which set of validators to run (default: input)",
    )
    parser.add_argument(
        "--from-model-card",
        type=str,
        metavar="MODEL_CARD_JSON",
        help="Path to an RT-AI-Model-Card JSON export; generates guardrail spec automatically",
    )
    parser.add_argument(
        "--generate-spec",
        type=str,
        metavar="OUTPUT_YAML",
        nargs="?",
        const="-",
        help=(
            "Generate a guardrail YAML spec from --from-model-card and write it to "
            "OUTPUT_YAML (use '-' or omit for stdout). Exits without running validation."
        ),
    )
    args = parser.parse_args(argv)

    # ------------------------------------------------------------------
    # Mode 1: --from-model-card + --generate-spec  →  write spec and exit
    # ------------------------------------------------------------------
    if args.from_model_card and args.generate_spec is not None:
        from .model_card import load_model_card, model_card_to_yaml

        card = load_model_card(args.from_model_card)
        yaml_str = model_card_to_yaml(card)

        if args.generate_spec == "-":
            sys.stdout.write(yaml_str)
        else:
            Path(args.generate_spec).write_text(yaml_str, encoding="utf-8")
            print(f"Spec written to {args.generate_spec}")
        return 0

    # ------------------------------------------------------------------
    # Mode 2: --from-model-card + data  →  validate using generated spec
    # ------------------------------------------------------------------
    if args.from_model_card:
        if not args.data:
            # Accept data as the first positional even when --from-model-card is used
            if args.spec:
                # The user put data in the spec slot (positional)
                data_path_str = args.spec
            else:
                parser.error(
                    "--from-model-card requires either a data path argument "
                    "or --generate-spec"
                )
                return 1
        else:
            data_path_str = args.data

        from .model_card import load_model_card, model_card_to_spec

        card = load_model_card(args.from_model_card)
        spec = model_card_to_spec(card)

        try:
            data = load_data_from_path(Path(data_path_str))
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

    # ------------------------------------------------------------------
    # Mode 3: spec + data  →  existing behaviour
    # ------------------------------------------------------------------
    if not args.spec or not args.data:
        parser.error(
            "Provide either (1) spec and data positional arguments, or "
            "(2) --from-model-card with a data path or --generate-spec"
        )
        return 1

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
