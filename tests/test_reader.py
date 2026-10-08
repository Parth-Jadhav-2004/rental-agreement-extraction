from src.checks import normalize_quote, output_issues
from src.config import FEW_SHOT_FILES
from src.prompt import load_few_shot_records
from src.reader import find_document, logical_stem, prepare
from src.schema import AgreementExtraction
from src.splits import file_names_for


def test_logical_stem_strips_pdf_docx():
    from pathlib import Path

    assert logical_stem(Path("156155545-Rental-Agreement-Kns-Home.pdf.docx")) == (
        "156155545-Rental-Agreement-Kns-Home"
    )


def test_overlap_file_is_found_in_the_test_folder():
    path = find_document("24158401-Rental-Agreement")
    assert path.parent.name == "test"
    assert path.suffix == ".png"


def test_few_shot_examples_drop_unrelated_clauses():
    from src.prompt import example_text, load_few_shot_records

    record = next(
        item
        for item in load_few_shot_records()
        if item["file_name"] == "6683129-House-Rental-Contract-Geraldine-Galinato-v2"
    )
    document = prepare(record["file_name"])
    excerpt = example_text(document, record)
    assert len(excerpt) < len(document.text) / 2
    assert "15 days" in excerpt


def test_few_shot_quotes_are_in_the_source_documents():
    assert tuple(record["file_name"] for record in load_few_shot_records()) == FEW_SHOT_FILES
    for record in load_few_shot_records():
        document = prepare(record["file_name"])
        extraction = AgreementExtraction.model_validate(record["extraction"])
        assert output_issues(extraction, document) == []
        assert normalize_quote(extraction.party_one_quote) in normalize_quote(document.text)


def test_dev_and_few_shot_do_not_overlap_and_test_includes_the_shared_file():
    dev = set(file_names_for("dev"))
    few_shot = set(FEW_SHOT_FILES)
    test = set(file_names_for("test"))
    assert dev.isdisjoint(few_shot)
    assert "24158401-Rental-Agreement" in test
    assert "24158401-Rental-Agreement" not in file_names_for("train")
