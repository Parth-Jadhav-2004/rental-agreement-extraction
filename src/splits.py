"""Which labeled files belong to each run."""

from src.config import DEV_FILES, OVERLAP_FILE, TEST_CSV, TRAIN_CSV
from src.evaluate import read_csv_rows


def file_names_for(split: str) -> list[str]:
    if split == "dev":
        return list(DEV_FILES)
    if split == "test":
        return [row["File Name"] for row in read_csv_rows(TEST_CSV)]
    if split == "train":
        names = [row["File Name"] for row in read_csv_rows(TRAIN_CSV)]
        return [name for name in names if name != OVERLAP_FILE]
    raise ValueError(f"Unknown split {split!r}. Use dev, test, or train.")


def gold_rows_for(split: str) -> list[dict[str, str]]:
    if split == "test":
        return read_csv_rows(TEST_CSV)
    wanted = set(file_names_for(split))
    return [row for row in read_csv_rows(TRAIN_CSV) if row["File Name"] in wanted]
