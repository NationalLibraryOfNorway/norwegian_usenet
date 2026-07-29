"""
Demonstrates that pandas silently converts certain strings to NaN when reading CSVs.
Strings like 'n/a', 'NA', 'null', 'none' etc. are in pandas' default NA list.
This caused a bug where 'n/a' email addresses written to CSV were read back as NaN,
making them undetectable as existing entries and causing hash collisions.
The fix is to use keep_default_na=False when reading the mapping CSVs.
"""

import io

import pandas as pd

NA_STRINGS = ["n/a", "N/A", "NA", "null", "NULL", "None", "nan", "NaN"]


def test_pandas_converts_na_strings_to_nan_by_default():
    for value in NA_STRINGS:
        csv = f"email,hashed_email\n{value},somehash\n"
        df = pd.read_csv(io.StringIO(csv))
        assert pd.isna(df["email"].iloc[0]), f"Expected '{value}' to be read as NaN"


def test_keep_default_na_false_preserves_na_strings():
    for value in NA_STRINGS:
        csv = f"email,hashed_email\n{value},somehash\n"
        df = pd.read_csv(io.StringIO(csv), keep_default_na=False)
        assert df["email"].iloc[0] == value, (
            f"Expected '{value}' to be preserved as string"
        )
