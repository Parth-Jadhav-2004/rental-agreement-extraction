from src.checks import drop_ungrounded, normalize_quote, output_issues, valid_date_token
from src.reader import PreparedDocument
from src.schema import AgreementExtraction


def _doc(text: str) -> PreparedDocument:
    return PreparedDocument("sample", path=None, modality="text", text=text, image_bytes=None, media_type=None)  # type: ignore[arg-type]


def _extraction(**overrides) -> AgreementExtraction:
    payload = {
        "agreement_value": 10000,
        "agreement_value_quote": "rent of Rs. 10,000",
        "agreement_start_date": "01.04.2010",
        "agreement_start_date_quote": "beginning 01.04.2010",
        "agreement_end_date": "30.03.2011",
        "agreement_end_date_quote": "ending 30.03.2011",
        "renewal_notice_days": None,
        "renewal_notice_days_quote": "",
        "party_one": "A Owner",
        "party_one_quote": "A Owner, lessor",
        "party_two": "B Tenant",
        "party_two_quote": "B Tenant, lessee",
    }
    payload.update(overrides)
    return AgreementExtraction.model_validate(payload)


def test_valid_date_accepts_impossible_calendar_days():
    assert valid_date_token("31.11.2009")
    assert valid_date_token("31.02.2011")
    assert not valid_date_token("1.4.2010")
    assert not valid_date_token("32.01.2010")


def test_quote_matches_across_whitespace_and_curly_quotes():
    document = _doc('The rent is Rs. 10,000\nper "month".')
    extraction = _extraction(
        agreement_value_quote='The rent is  Rs. 10,000 per \u201cmonth\u201d.',
        agreement_start_date_quote="beginning 01.04.2010",
        agreement_end_date_quote="ending 30.03.2011",
        party_one_quote="A Owner, lessor",
        party_two_quote="B Tenant, lessee",
    )
    document = PreparedDocument(
        "sample",
        path=document.path,
        modality="text",
        text='The rent is Rs. 10,000\nper "month". beginning 01.04.2010 ending 30.03.2011 A Owner, lessor B Tenant, lessee',
        image_bytes=None,
        media_type=None,
    )
    assert output_issues(extraction, document) == []
    assert "month" in normalize_quote(extraction.agreement_value_quote)


def test_missing_quote_is_reported_and_then_dropped():
    document = _doc("The rent is Rs. 10,000. beginning 01.04.2010 ending 30.03.2011 A Owner, lessor B Tenant, lessee")
    extraction = _extraction(agreement_value_quote="this quote is not in the document")
    issues = output_issues(extraction, document)
    assert any("agreement_value" in issue for issue in issues)
    cleaned = drop_ungrounded(extraction, document)
    assert cleaned.agreement_value is None
    assert cleaned.agreement_value_quote == ""
    assert cleaned.party_one == "A Owner"


def test_image_documents_do_not_require_the_quote_to_match_pixels():
    document = PreparedDocument(
        "scan",
        path=None,  # type: ignore[arg-type]
        modality="image",
        text="",
        image_bytes=b"png",
        media_type="image/png",
    )
    extraction = _extraction()
    assert output_issues(extraction, document) == []
