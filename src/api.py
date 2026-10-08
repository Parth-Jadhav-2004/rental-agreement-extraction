"""Optional HTTP wrapper around the same extractor the batch script uses."""

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.client import ExtractorError, build_client
from src.config import FIELDS
from src.pipeline import extract_document, latest_cached_record, prediction_row
from src.reader import IMAGE_SUFFIXES, PreparedDocument, prepare, read_docx

app = FastAPI(title="Rental agreement extraction", version="1.0.0")
PAGE = Path(__file__).with_name("try_page.html")

SAMPLES = (
    "50070534-RENTAL-AGREEMENT",
    "228094620-Rental-Agreement",
    "95980236-Rental-Agreement",
    "try-pune-apartment",
    "try-kochi-house",
    "try-jaipur-flat",
)


def _prepare_upload(name: str, data: bytes) -> PreparedDocument:
    suffix = Path(name).suffix.lower()
    logical = Path(name).name
    for ending in (".pdf.docx", ".docx", ".png", ".jpg", ".jpeg", ".webp"):
        if logical.lower().endswith(ending):
            logical = logical[: -len(ending)]
            break
    with tempfile.NamedTemporaryFile(suffix=suffix or ".bin", delete=False) as handle:
        handle.write(data)
        temporary = Path(handle.name)
    try:
        if name.lower().endswith(".docx") or suffix == ".docx":
            text = read_docx(temporary)
            return PreparedDocument(logical, temporary, "text", text, None, None)
        if suffix in IMAGE_SUFFIXES:
            from src.reader import MEDIA_TYPES

            return PreparedDocument(
                logical, temporary, "image", "", data, MEDIA_TYPES[suffix]
            )
        raise HTTPException(status_code=400, detail="Upload a .docx or .png file.")
    finally:
        temporary.unlink(missing_ok=True)


def _response(record: dict) -> dict:
    return {
        "file_name": record["file_name"],
        "fields": {field: record["extraction"][field] for field in FIELDS},
        "quotes": {field: record["extraction"][f"{field}_quote"] for field in FIELDS},
        "csv_row": prediction_row(record),
        "issues_after_repair": record["issues_after_repair"],
    }


def _run(document: PreparedDocument) -> dict:
    cached = latest_cached_record(document.file_name)
    if cached is not None:
        return _response(cached)
    if document.modality == "text" and not document.text.strip():
        raise HTTPException(status_code=400, detail="The document contained no text.")
    try:
        record = extract_document(document, client=build_client(), force=False)
    except ExtractorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _response(record)


@app.get("/")
def home():
    from fastapi.responses import HTMLResponse

    return HTMLResponse(PAGE.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract")
def extract(file: UploadFile = File(...)) -> dict:
    filename = file.filename or "upload"
    data = file.file.read()
    return _run(_prepare_upload(filename, data))


@app.post("/extract/sample/{file_name}")
def extract_sample(file_name: str) -> dict:
    if file_name not in SAMPLES:
        raise HTTPException(status_code=404, detail="That sample is not available.")
    try:
        document = prepare(file_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _run(document)
