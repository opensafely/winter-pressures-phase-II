"""Check raw measures output for duplicate practice-measure-interval rows.

This is a small audit script for files like:
--path output/practice_measures_resp/practice_measures_2023-05-08_test.csv

It prints a summary of duplicate key groups and then shows the matching raw
rows so duplicates are easy to inspect.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_KEYS = ["practice_pseudo_id", "measure", "interval_start"]


def load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".arrow":
        return pd.read_feather(path)
    raise ValueError(f"Unsupported file type: {path.suffix}. Use .csv or .arrow")


def print_duplicate_groups(df: pd.DataFrame, keys: list[str], max_groups: int, max_rows_per_group: int) -> None:
    duplicate_mask = df.duplicated(subset=keys, keep=False)
    duplicate_rows = df.loc[duplicate_mask].copy()

    print(f"rows={len(df)}")
    print(f"duplicate_rows={int(duplicate_mask.sum())}")
    print(f"duplicate_key_groups={duplicate_rows.groupby(keys, observed=True).ngroups}")

    if duplicate_rows.empty:
        print("No duplicates found for the selected keys.")
        return

    summary = (
        duplicate_rows.groupby(keys, observed=True)
        .size()
        .reset_index(name="n_rows")
        .sort_values(["n_rows"] + keys, ascending=[False] + [True] * len(keys))
    )

    print("\nTop duplicate key groups:")
    print(summary.head(max_groups).to_string(index=False))

    duplicate_rows = duplicate_rows.reset_index(names="source_row")
    other_columns = [col for col in duplicate_rows.columns if col not in {"source_row", *keys}]
    show_columns = ["source_row", *keys, *other_columns]

    print("\nMatching duplicate rows:")
    for group_index, (group_values, group_df) in enumerate(duplicate_rows.groupby(keys, observed=True), start=1):
        if group_index > max_groups:
            break

        if not isinstance(group_values, tuple):
            group_values = (group_values,)
        group_label = ", ".join(f"{key}={value}" for key, value in zip(keys, group_values))
        print(f"\n[{group_index}] {group_label} (n_rows={len(group_df)})")
        print(group_df.head(max_rows_per_group)[show_columns].to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check raw measures output for duplicate intervals.")
    parser.add_argument("--path", help="Path to a raw measures .csv or .arrow file")
    parser.add_argument(
        "--keys",
        default=",".join(DEFAULT_KEYS),
        help="Comma-separated key columns to use for duplicate detection",
    )
    parser.add_argument(
        "--max-groups",
        type=int,
        default=10,
        help="Maximum number of duplicate key groups to print",
    )
    parser.add_argument(
        "--max-rows-per-group",
        type=int,
        default=10,
        help="Maximum number of raw rows to print per duplicate group",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.path)
    keys = [key.strip() for key in args.keys.split(",") if key.strip()]

    df = load_table(path)
    missing_keys = [key for key in keys if key not in df.columns]
    if missing_keys:
        raise ValueError(f"Missing key columns in {path}: {', '.join(missing_keys)}")

    print(f"file={path}")
    print(f"keys={keys}")
    print_duplicate_groups(df, keys, args.max_groups, args.max_rows_per_group)


if __name__ == "__main__":
    main()