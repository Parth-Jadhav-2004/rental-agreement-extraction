from src.evaluate import collapsed, score_rows


def test_exact_recall_counts_blanks_and_keeps_spaces():
    gold = [
        {
            "File Name": "a",
            "Aggrement Value": "6500",
            "Aggrement Start Date": "20.05.2007",
            "Aggrement End Date": "20.05.2008",
            "Renewal Notice (Days)": "",
            "Party One": "Hanumaiah ",
            "Party Two": "Vishal",
        }
    ]
    predicted = [
        {
            "File Name": "a",
            "Aggrement Value": "6500",
            "Aggrement Start Date": "20.05.2007",
            "Aggrement End Date": "20.05.2008",
            "Renewal Notice (Days)": "",
            "Party One": "Hanumaiah",
            "Party Two": "Vishal",
        }
    ]
    result = score_rows(gold, predicted)
    assert result["per_field"]["agreement_value"]["exact_recall"] == 1
    assert result["per_field"]["renewal_notice_days"]["exact_recall"] == 1
    assert result["per_field"]["party_one"]["exact_recall"] == 0
    assert result["per_field"]["party_one"]["trimmed_recall"] == 1
    assert result["micro_exact_recall"] == 5 / 6


def test_missing_prediction_is_a_miss():
    gold = [
        {
            "File Name": "a",
            "Aggrement Value": "1",
            "Aggrement Start Date": "",
            "Aggrement End Date": "",
            "Renewal Notice (Days)": "",
            "Party One": "",
            "Party Two": "",
        }
    ]
    result = score_rows(gold, [])
    assert result["per_field"]["agreement_value"]["exact_true"] == 0
    assert result["per_field"]["party_one"]["exact_true"] == 0


def test_collapsed_whitespace_helper():
    assert collapsed("  A   B ") == "A B"
    assert collapsed(None) == ""
