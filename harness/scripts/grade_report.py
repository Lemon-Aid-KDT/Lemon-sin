"""Grade a saved Lemon Aid Agent harness report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", help="Path to a JSON report from run_harness.py")
    args = parser.parse_args()

    path = Path(args.report)
    report = json.loads(path.read_text(encoding="utf-8"))
    summary = report["summary"]

    print(f"total={summary['total']} passed={summary['passed']} failed={summary['failed']}")
    for result in report["results"]:
        status = result["status"]
        print(f"{status}: {result['scenario_id']}")
        for failure in result["failures"]:
            print(f"  - {failure}")

    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

