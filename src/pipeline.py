"""Extract one document, check quotes, and allow one repair call."""

import json
from pathlib import Path

from src.checks import drop_ungrounded, output_issues
from src.client import build_client, complete
from src.config import FIELDS, MODEL, PREDICTIONS_DIR, PROMPT_VERSION
from src.prompt import build_messages
from src.reader import PreparedDocument, prepare
from src.schema import AgreementExtraction


def cache_path(file_name: str) -> Path:
    safe = file_name.replace("/", "_")
    return PREDICTIONS_DIR / "cache" / PROMPT_VERSION / f"{safe}.json"


def latest_cached_record(file_name: str) -> dict | None:
    """Return the newest saved extraction for this file, from any prompt version."""
    safe = file_name.replace("/", "_")
    root = PREDICTIONS_DIR / "cache"
    if not root.exists():
        return None
    matches = [path for path in root.glob(f"*/{safe}.json") if path.is_file()]
    if not matches:
        return None
    newest = max(matches, key=lambda path: path.stat().st_mtime)
    return json.loads(newest.read_text(encoding="utf-8"))


def _record(document: PreparedDocument, extraction: AgreementExtraction, issues: list[str], repaired: bool) -> dict:
    return {
        "file_name": document.file_name,
        "source_path": str(document.path),
        "modality": document.modality,
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "repaired": repaired,
        "issues_after_repair": issues,
        "extraction": extraction.model_dump(),
    }


def extract_document(document: PreparedDocument, client=None, force: bool = False) -> dict:
    path = cache_path(document.file_name)
    if path.exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))

    if client is None:
        client = build_client()
    messages = build_messages(document)
    extraction = complete(client, messages)
    issues = output_issues(extraction, document)
    repaired = False
    if issues:
        repaired = True
        messages = list(messages)
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(extraction.model_dump(), ensure_ascii=False),
            }
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "The extraction failed these checks:\n- "
                    + "\n- ".join(issues)
                    + "\nReturn a corrected JSON object. Copy quotes from the document. "
                    "If you cannot ground a field, set that value to null and its quote to an empty string."
                ),
            }
        )
        extraction = complete(client, messages)
        issues = output_issues(extraction, document)
        extraction = drop_ungrounded(extraction, document)
        issues = output_issues(extraction, document)

    record = _record(document, extraction, issues, repaired)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def extract_file_name(file_name: str, client=None, force: bool = False) -> dict:
    return extract_document(prepare(file_name), client=client, force=force)


def prediction_row(record: dict) -> dict[str, str]:
    payload = record["extraction"]
    row = {"File Name": record["file_name"]}
    from src.config import FIELD_TO_COLUMN

    for field in FIELDS:
        value = payload[field]
        row[FIELD_TO_COLUMN[field]] = "" if value is None else str(value)
    return row
