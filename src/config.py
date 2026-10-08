"""Runtime settings for the Muse Spark extractor."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TRAIN_DIR = DATA_DIR / "train"
TEST_DIR = DATA_DIR / "test"
TRAIN_CSV = DATA_DIR / "train.csv"
TEST_CSV = DATA_DIR / "test.csv"
PREDICTIONS_DIR = ROOT / "predictions"
PROMPT_VERSION = "v3"

MODEL = "muse-spark-1.3-contributor"
BASE_URL = "https://api.meta.ai/v1"
API_KEY_ENV = "MODEL_API_KEY"
REASONING_EFFORT = "low"
SEED = 7
MAX_COMPLETION_TOKENS = 4000
PROMPT_CACHE_KEY = "agreement-extract-v3"
REQUEST_TIMEOUT_SECONDS = 180

# Held out of the prompt. Used to check the extractor before the test files are scored.
DEV_FILES = (
    "18325926-Rental-Agreement-1",
    "36199312-Rental-Agreement",
    "47854715-RENTAL-AGREEMENT",
)

# Labeled documents shown to the model as worked examples. Not part of the dev set.
# 24158401 is excluded: it is labeled in train.csv and stored under data/test.
FEW_SHOT_FILES = (
    "50070534-RENTAL-AGREEMENT",
    "6683129-House-Rental-Contract-Geraldine-Galinato-v2",
)

OVERLAP_FILE = "24158401-Rental-Agreement"

CSV_COLUMNS = (
    "File Name",
    "Aggrement Value",
    "Aggrement Start Date",
    "Aggrement End Date",
    "Renewal Notice (Days)",
    "Party One",
    "Party Two",
)

FIELD_TO_COLUMN = {
    "agreement_value": "Aggrement Value",
    "agreement_start_date": "Aggrement Start Date",
    "agreement_end_date": "Aggrement End Date",
    "renewal_notice_days": "Renewal Notice (Days)",
    "party_one": "Party One",
    "party_two": "Party Two",
}

FIELDS = tuple(FIELD_TO_COLUMN)
