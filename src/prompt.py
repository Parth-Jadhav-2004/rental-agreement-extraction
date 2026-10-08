"""Prompt and few-shot examples. Examples are document-faithful, not label-corrected."""

import json
from pathlib import Path

from src.checks import normalize_quote
from src.config import FEW_SHOT_FILES, PROMPT_VERSION, ROOT
from src.reader import PreparedDocument, image_for_model, prepare
from src.schema import AgreementExtraction

FEW_SHOT_PATH = ROOT / "prompts" / "few_shot.json"

INSTRUCTIONS = """You extract metadata from a rental agreement. The response must match the JSON schema.

Field rules:
- agreement_value is the recurring rent, not the security deposit, advance, or maintenance charge. Return an integer with no currency sign and no separators. "Rs. 10,000" is 10000. "Rs.4,000.00" is 4000. A figure written as 6.500.00 together with the words "six thousand five hundred" is 6500. When the digits are a plain amount, use the digits even if the words beside them disagree: "Rs.3800/- (Rupees Thirty Eight Thousand Only)" is 3800. Use the words only when the figure itself is damaged, such as "Rs.12, OOO" beside "Twelve Thousand".
- agreement_start_date and agreement_end_date are the lease term, formatted DD.MM.YYYY with leading zeros. Use the term dates when the signing date is different. Copy a printed end date, including a day that is calendrically impossible. If the term is only a start date plus a number of months, the end date is one day before the same day that many months later. Eleven months from 5 December 2008 ends on 04.11.2009. Eleven months from 1 April 2010 ends on 31.03.2011 only when the contract prints that end date; otherwise 1 April plus 11 months minus one day is 28.02.2011 in a non-leap year.
- renewal_notice_days is the notice required to terminate, vacate, or end the tenancy, converted to days. Use 30 days for each month stated. "three month advance notice" is 90. "one month notice" is 30. When the contract gives both a notice to terminate and a separate notice only for asking to renew, use the notice to terminate or vacate. Return null when no notice period is stated. A grace period for late rent is not the notice period.
- party_one is the side granting the premises: lessor, landlord, owner, house owner, management, or party of the first part. party_two is the side taking the premises: lessee, tenant, resident, or party of the second part. Copy the name as printed. Omit honorifics such as Mr, Mrs, Sri, and Smt. Omit age, parentage, and address. Keep joint parties in the order printed, including "and/or" or "&".
- Every non-null value needs a quote copied from the document, not a paraphrase. For a date or day-count you calculated, quote the clause you calculated from. A null value has an empty quote.
- Do not invent a value that the document does not support.
"""


def load_few_shot_records() -> list[dict]:
    payload = json.loads(FEW_SHOT_PATH.read_text(encoding="utf-8"))
    names = [record["file_name"] for record in payload]
    if tuple(names) != FEW_SHOT_FILES:
        raise ValueError(f"prompts/few_shot.json must list {FEW_SHOT_FILES} in that order")
    return payload


def example_text(document: PreparedDocument, record: dict) -> str:
    """Keep only the paragraphs that contain the example quotes."""
    quotes = [
        value
        for key, value in record["extraction"].items()
        if key.endswith("_quote") and value
    ]
    kept = []
    for paragraph in document.text.split("\n"):
        folded = normalize_quote(paragraph)
        if any(normalize_quote(quote) in folded for quote in quotes):
            kept.append(paragraph)
    return "\n".join(kept) if kept else document.text


def render_example(record: dict, document: PreparedDocument) -> str:
    extraction = AgreementExtraction.model_validate(record["extraction"])
    body = json.dumps(extraction.model_dump(), ensure_ascii=False, indent=2)
    return f"EXAMPLE DOCUMENT:\n{example_text(document, record)}\n\nEXAMPLE OUTPUT:\n{body}"


def example_blocks(target_file_name: str) -> str:
    blocks = []
    for record in load_few_shot_records():
        if record["file_name"] == target_file_name:
            continue
        document = prepare(record["file_name"])
        blocks.append(render_example(record, document))
    return "\n\n".join(blocks)


def build_messages(document: PreparedDocument) -> list[dict]:
    examples = example_blocks(document.file_name)
    if document.modality == "text":
        user_text = (
            f"{examples}\n\nDOCUMENT TO EXTRACT:\n{document.text}\n\n"
            "Extract the six fields from the document to extract."
        )
        return [
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": user_text},
        ]

    if document.image_bytes is None or document.media_type is None:
        raise ValueError(f"{document.file_name} is marked as an image but has no bytes")
    import base64

    image_bytes, media_type = image_for_model(document.image_bytes, document.media_type)
    encoded = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{media_type};base64,{encoded}"
    user_text = (
        f"{examples}\n\nThe rental agreement to extract is the attached page image. "
        "Read the page and extract the six fields. Quotes must be text you can see on the page."
    )
    return [
        {"role": "system", "content": INSTRUCTIONS},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]


def prompt_version() -> str:
    return PROMPT_VERSION
