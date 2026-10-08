"""Validate model output. These checks do not search the document for fields."""

from src.config import FIELDS
from src.reader import PreparedDocument
from src.schema import AgreementExtraction


def collapse(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def normalize_quote(value: str) -> str:
    swapped = (
        value.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    return collapse(swapped)


def valid_date_token(value: str) -> bool:
    pieces = value.split(".")
    if len(pieces) != 3:
        return False
    day, month, year = pieces
    if not (len(day) == 2 and len(month) == 2 and len(year) == 4):
        return False
    if not (day.isdigit() and month.isdigit() and year.isdigit()):
        return False
    return 1 <= int(day) <= 31 and 1 <= int(month) <= 12


def output_issues(extraction: AgreementExtraction, document: PreparedDocument) -> list[str]:
    """Return problems that a single repair call is allowed to fix."""
    problems = []
    source = normalize_quote(document.text) if document.modality == "text" else ""
    payload = extraction.model_dump()
    for field in FIELDS:
        value = payload[field]
        quote = payload[f"{field}_quote"] or ""
        if value is None:
            if quote.strip():
                problems.append(f"{field}: null value must have an empty quote")
            continue
        if field.endswith("_date") and not valid_date_token(str(value)):
            problems.append(f"{field}: {value!r} is not DD.MM.YYYY")
        if not quote.strip():
            problems.append(f"{field}: a non-null value needs a source quote")
            continue
        if document.modality == "text" and normalize_quote(quote) not in source:
            problems.append(f"{field}: quote was not found in the document")
    return problems


def drop_ungrounded(extraction: AgreementExtraction, document: PreparedDocument) -> AgreementExtraction:
    """Blank text-document fields whose quote is still not in the source after repair."""
    if document.modality != "text":
        return extraction
    source = normalize_quote(document.text)
    payload = extraction.model_dump()
    for field in FIELDS:
        value = payload[field]
        quote = payload[f"{field}_quote"] or ""
        invalid_date = field.endswith("_date") and value is not None and not valid_date_token(str(value))
        missing_quote = value is not None and normalize_quote(quote) not in source
        if invalid_date or missing_quote:
            payload[field] = None
            payload[f"{field}_quote"] = ""
    return AgreementExtraction.model_validate(payload)
