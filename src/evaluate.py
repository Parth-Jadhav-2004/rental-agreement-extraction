"""Per-field exact recall, plus the same score after whitespace is collapsed."""

import csv
from pathlib import Path

from src.config import CSV_COLUMNS, FIELD_TO_COLUMN, FIELDS, TEST_CSV, TRAIN_CSV


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CSV_COLUMNS})


def cell(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def collapsed(value: object) -> str:
    return " ".join(cell(value).split())


def score_rows(gold_rows: list[dict[str, str]], prediction_rows: list[dict[str, str]]) -> dict:
    predictions = {row["File Name"]: row for row in prediction_rows}
    exact_true = {field: 0 for field in FIELDS}
    trimmed_true = {field: 0 for field in FIELDS}
    misses = []
    for gold in gold_rows:
        file_name = gold["File Name"]
        predicted = predictions.get(file_name)
        if predicted is None:
            for field, column in FIELD_TO_COLUMN.items():
                misses.append(
                    {
                        "file_name": file_name,
                        "field": field,
                        "gold": cell(gold.get(column, "")),
                        "predicted": "",
                    }
                )
            continue
        for field, column in FIELD_TO_COLUMN.items():
            gold_value = gold.get(column, "")
            pred_value = predicted.get(column, "")
            if cell(gold_value) == cell(pred_value):
                exact_true[field] += 1
            else:
                misses.append(
                    {
                        "file_name": file_name,
                        "field": field,
                        "gold": cell(gold_value),
                        "predicted": cell(pred_value),
                    }
                )
            if collapsed(gold_value) == collapsed(pred_value):
                trimmed_true[field] += 1
    total = len(gold_rows)
    per_field = {}
    for field in FIELDS:
        per_field[field] = {
            "exact_recall": (exact_true[field] / total) if total else 0.0,
            "trimmed_recall": (trimmed_true[field] / total) if total else 0.0,
            "exact_true": exact_true[field],
            "trimmed_true": trimmed_true[field],
            "total": total,
        }
    exact_hits = sum(exact_true.values())
    trimmed_hits = sum(trimmed_true.values())
    slots = total * len(FIELDS)
    return {
        "documents": total,
        "per_field": per_field,
        "micro_exact_recall": (exact_hits / slots) if slots else 0.0,
        "micro_trimmed_recall": (trimmed_hits / slots) if slots else 0.0,
        "misses": misses,
    }


def gold_path_for(split: str) -> Path:
    if split == "test":
        return TEST_CSV
    if split in {"dev", "train"}:
        return TRAIN_CSV
    raise ValueError(f"Unknown split {split!r}")


def format_report(result: dict) -> str:
    lines = [
        f"documents: {result['documents']}",
        f"micro exact recall: {result['micro_exact_recall']:.3f}",
        f"micro trimmed recall: {result['micro_trimmed_recall']:.3f}",
        "",
        f"{'field':<24} {'exact':>8} {'trimmed':>8}",
    ]
    for field, scores in result["per_field"].items():
        lines.append(
            f"{field:<24} {scores['exact_recall']:>8.3f} {scores['trimmed_recall']:>8.3f}"
        )
    if result["misses"]:
        lines.append("")
        lines.append("misses:")
        for miss in result["misses"]:
            lines.append(
                f"- {miss['file_name']} | {miss['field']} | gold={miss['gold']!r} | predicted={miss['predicted']!r}"
            )
    return "\n".join(lines)
