from __future__ import annotations

import argparse
import sys

from .core import validate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="loomground_composition",
        description="Descriptive, plane-neutral composition validator (structural only).",
    )
    p.add_argument("composition", help="grounding-pipeline or governed-loop")
    p.add_argument("--catalogue", default=None, help="path to CATALOGUE.json")
    args = p.parse_args(argv)

    report = validate(args.composition, catalogue_path=args.catalogue)
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
