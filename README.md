# Rental agreement metadata extraction

Extracts six fields from rental agreements supplied as Word files or page scans:

- Agreement value (monthly rent)
- Agreement start date
- Agreement end date
- Renewal notice, in days
- Party one (the owner side)
- Party two (the tenant side)

The extractor is Muse Spark 1.3 Contributor (`muse-spark-1.3-contributor`) on the Meta Model API. Word files are read with `python-docx` and sent as text. Scans are sent as page images. The model returns JSON constrained to a schema, including the clause it used for each field. A quote that does not appear in a Word file is rejected. The assignment metric is exact per-field recall.

## Why this setup

There are about ten labeled agreements, and the templates are not the same. Fine-tuning a layout model on that set would memorize these pages. The field values are also not always a single printed span: "three month advance notice" has to become `90`, and a term given only as a start date plus a number of months has to become an end date. Muse Spark reads both text and images and can follow that schema without a hand-written pattern for each template.

Contributor pricing is $0.10 per million input tokens and $0.20 per million output tokens. Prompts and completions on this tier may be used to train future Meta models. These contracts contain names and addresses.

`temperature` is left at the API default. Muse Spark is tuned for that default, and disabling reasoning returns HTTP 400. Requests use `reasoning_effort: "low"` and `seed: 7`. Example contracts are sent as the clauses that support the answer, and a file that was already extracted is returned from the local cache.

## Field rules

The model is instructed to:

- Return the recurring rent as an integer, and leave out the deposit and the advance.
- Use the lease term rather than the signing date when those differ, formatted `DD.MM.YYYY`.
- Copy a printed end date. If only a start and a number of months are printed, the end date is one day before the same day that many months later.
- Convert a notice stated in months at 30 days per month. When both a termination notice and a separate renewal-request notice appear, use the termination notice. That is the figure the labels follow.
- Copy party names without honorifics, age, or address. Party one grants the premises. Party two takes them.

Checked after the model responds, and not used to find the fields:

- A date must look like `DD.MM.YYYY`. Impossible days such as `31.02.2011` are allowed, because a printed date should be copied.
- For a Word file, each quote must occur in the extracted text. One repair call is made when a check fails. A field that is still ungrounded is left blank and counts as a miss.

## Label audit

Several labels do not match the text. Exact recall treats those as misses. They are properties of the CSV, and the predictions are not edited to agree with them.

| Issue | What is going on |
|---|---|
| `24158401-Rental-Agreement` | Labeled in `train.csv` and stored under `data/test/`. It is scored with the test split only, and it is not a few-shot example. |
| `46239065-Standard-Rental-Agreement-Rental-With-Performance-Fee.docx` | Present in `train/` with no label row. It is not scored. |
| `6683127` page-1 file | The label's 15-day notice is not in this excerpt. The full contract `6683129` does contain "written notice of at least 15 days". |
| Galinato names | The recital says `GERALDINE O. GALINATO` and `Ingles. Jr.` The signature block says `GERALDINE Q. GALINATO` and `Ingles, Jr.` The CSV uses the signature spelling. |
| Impossible end dates | `31.11.2009`, `31.02.2011`, and `31.04.2011` are not real calendar days. They show up where the sheet forces day 31. |
| `44737744` | The Word text is already garbled (`RENTfft`, `Rs 9.99.7.9°`). The rent and the dates in the CSV cannot be read from that file. |
| Party cells | Several labels have stray spaces (`Hanumaiah `, ` P C MATHEW`). Trimmed recall is reported beside exact recall so that formatting is visible separately. |
| Column names | The CSV spells the columns `Aggrement Value`, `Aggrement Start Date`, and `Aggrement End Date`. Predictions use those names. |

## Split

Few-shot examples, kept out of the development set:

- `50070534-RENTAL-AGREEMENT`
- `6683129-House-Rental-Contract-Geraldine-Galinato-v2`

Development files, used to see whether the prompt is behaving before the test files are scored:

- `18325926-Rental-Agreement-1`
- `36199312-Rental-Agreement` (scan)
- `47854715-RENTAL-AGREEMENT`

The test split is every row in `data/test.csv`.

## Run

```bash
pip install -r requirements.txt
```

Put the Meta Model API key in the environment or in a `.env` file:

```bash
MODEL_API_KEY=your_key
```

From the project root:

```bash
python -m src.cli extract --split dev
python -m src.cli evaluate --split dev
python -m src.cli extract --split test
python -m src.cli evaluate --split test
```

Cached responses live in `predictions/cache/v3/`. Pass `--force` to call the model again. Each run writes `predictions/<split>_predictions.csv`, `predictions/<split>_details.json` (quotes included), and `predictions/<split>_recall.txt`.

Unit tests cover the scorer, the quote check, and the file split. They do not call the API.

```bash
python -m pytest
```

## API

The batch script and the service call the same function.

```bash
uvicorn src.api:app --reload
```

```bash
curl -F "file=@data/train/50070534-RENTAL-AGREEMENT.docx" http://127.0.0.1:8000/extract
```

`GET /health` returns `{"status": "ok"}`.

## Results

Prompt version `v2`. The development split was scored while the instruction was being checked. The test split was scored once after that.

Development, 3 documents:

| Field | Exact recall | Trimmed recall |
|---|---:|---:|
| Agreement value | 1.000 | 1.000 |
| Start date | 1.000 | 1.000 |
| End date | 0.000 | 0.000 |
| Renewal notice | 1.000 | 1.000 |
| Party one | 0.000 | 0.667 |
| Party two | 0.333 | 1.000 |
| All fields | 0.556 | 0.778 |

Test, 4 documents:

| Field | Exact recall | Trimmed recall |
|---|---:|---:|
| Agreement value | 1.000 | 1.000 |
| Start date | 1.000 | 1.000 |
| End date | 0.750 | 0.750 |
| Renewal notice | 1.000 | 1.000 |
| Party one | 0.000 | 1.000 |
| Party two | 0.250 | 0.500 |
| All fields | 0.667 | 0.875 |

Every party-one miss on the test set is a leading or trailing space in the CSV. The names themselves match. The remaining misses are:

- `95980236` prints an 11-month term from 1 April 2010 and no end date. The extractor returns `28.02.2011`. The CSV says `31.03.2011`.
- `156155545` party two keeps the printed honorific `SRI` and a final period. The CSV drops both.
- `228094620` party two is `B.Kishore`. The CSV cell is `.B.Kishore`, with a stray dot.

The three development end dates are the same kind of disagreement. The documents support `04.11.2009`, `31.03.2011`, and `28.02.2011`. The CSV has `31.11.2009`, `31.04.2011`, and `31.02.2011`.

## Layout

```text
src/            reader, schema, Muse client, quote check, CLI, API
prompts/        few-shot outputs, with quotes taken from the Word files
tests/          scorer, quote check, split
predictions/    created when you run extract
data/           agreements and label CSVs
```
