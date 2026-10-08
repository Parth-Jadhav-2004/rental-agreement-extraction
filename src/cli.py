"""Batch extraction and scoring."""

import argparse
import json
import sys

from src.client import build_client
from src.config import PREDICTIONS_DIR
from src.evaluate import format_report, score_rows, write_csv_rows
from src.pipeline import extract_file_name, prediction_row
from src.splits import file_names_for, gold_rows_for


def extract_split(split: str, force: bool) -> None:
    names = file_names_for(split)
    client = build_client()
    records = []
    for index, name in enumerate(names, start=1):
        print(f"[{index}/{len(names)}] {name}", flush=True)
        record = extract_file_name(name, client=client, force=force)
        issues = record["issues_after_repair"]
        status = "repaired" if record["repaired"] else "ok"
        if issues:
            status = f"{status}, {len(issues)} issue(s) left"
        print(f"    {status}", flush=True)
        records.append(record)
    rows = [prediction_row(record) for record in records]
    csv_path = PREDICTIONS_DIR / f"{split}_predictions.csv"
    details_path = PREDICTIONS_DIR / f"{split}_details.json"
    write_csv_rows(csv_path, rows)
    details_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {csv_path}")
    print(f"wrote {details_path}")


def evaluate_split(split: str) -> None:
    csv_path = PREDICTIONS_DIR / f"{split}_predictions.csv"
    if not csv_path.exists():
        raise SystemExit(f"No predictions at {csv_path}. Run extract --split {split} first.")
    from src.evaluate import read_csv_rows

    result = score_rows(gold_rows_for(split), read_csv_rows(csv_path))
    report = format_report(result)
    report_path = PREDICTIONS_DIR / f"{split}_recall.txt"
    report_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"wrote {report_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract rental-agreement metadata.")
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract", help="Run Muse Spark on a split.")
    extract.add_argument("--split", required=True, choices=("dev", "test", "train"))
    extract.add_argument("--force", action="store_true", help="Ignore cached model responses.")

    evaluate = sub.add_parser("evaluate", help="Score a predictions CSV against the labels.")
    evaluate.add_argument("--split", required=True, choices=("dev", "test", "train"))

    args = parser.parse_args(argv)
    if args.command == "extract":
        extract_split(args.split, args.force)
    else:
        evaluate_split(args.split)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
