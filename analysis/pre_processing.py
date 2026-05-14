# This script processes the raw measures output to generate patient-characteristic stratified measures
# Usage python analysis/pre_processing.py
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval

import json

import pandas as pd
from scipy import stats
import numpy as np
import argparse
from datetime import datetime, timedelta
import os
from utils import *
import pyarrow.feather as feather
from parse_args import config

# --------- Configuration ------------------------------------------------

dates = generate_annual_dates(config["study_end_date"], config["n_years"])

date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

if config["test"]:

    # For testing, use only one date
    dates = [config["test_config"]["start_date"]]

core_columns = [
    "practice_pseudo_id",
    "measure",
    "interval_start",
    "numerator",
    "list_size",
]

# -------- Patient measures processing ----------------------------------

# Instantiate list of yearly dataframes for each subgroup
measures_dict = {}

for subgroup in config["subgroups"]:
    measures_dict[subgroup] = []

log_memory_usage(label="Before loading data")
# Load and format data for each interval
for date in dates:

    print(f"Loading {config['group']} measures {date}", flush=True)
    input_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}/{config['group']}_measures_{date}"
    output_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}/proc_{config['group']}_measures"  # Read in measures
    df = read_write(read_or_write="read", path=input_path, dtype=config["dtype_dict"])

    # Count total rsv_specific cases in 2023 for sense check
    if config["set"] == "resp":
        print(
            column_total_check(
                df, column="numerator", year=2023, measure_name="rsv_specific"
            )
        )

    df.drop(
        columns=["interval_end", "ratio"], inplace=True
    )  # Drop interval end column as not needed for analysis and saves memory
    log_memory_usage(label=f"After loading measures {date}")
    print(f"Initial shape of input: {df.shape}", flush=True)

    # Rename denominator column to list_size
    df.rename(columns={"denominator": "list_size"}, inplace=True)
    print(f"Data types of input: {df.dtypes}", flush=True)
    nan_counts = df.isna().sum()
    print(
        f"""Number of NA's in each columns {nan_counts}\n
            count without 0 numerator: {df[(df['numerator'] > 0)].shape}\n
            count without nan numerator: {df[(df['numerator'].notna())].shape}\n
            count without 0 list_size: {df[(df['list_size'] > 0)].shape}\n
            count without nan list_size: {df[(df['list_size'].notna())].shape}""",
        flush=True,
    )

    # Drop rows with 0 list_size or nan list_size
    df = df[(df["list_size"] > 0) & (df["list_size"].notna())]
    print(
        f"After dropping rows with 0 list_size or nan list_size shape: {df.shape}",
        flush=True,
    )

    # Count total rsv_specific cases in 2023 for sense check
    if config["set"] == "resp":
        print(
            column_total_check(
                df, column="numerator", year=2023, measure_name="rsv_specific"
            )
        )

    # Loop through each subgroup and append the subgroups measures
    for subgroup in config["subgroups"]:

        core_columns_i = core_columns.copy()

        # Ethnicity_sus needed for imputation
        if subgroup == "ethnicity":
            core_columns_i = core_columns_i + ["ethnicity_sus"]

        if config["practice_subgroup_measures"]:
            subgroup_df = df[df["measure"].str.endswith(subgroup)]
        else:
            subgroup_df = df

        # Drop unneeded columns from each measure dataframe
        for col in subgroup_df.columns:

            # If the column is not the subgroup identifier or a core column, drop it to save memory
            if (not subgroup.endswith(col)) and (col not in core_columns_i):
                subgroup_df = subgroup_df.drop(columns=[col])

        measures_dict[subgroup].append(subgroup_df)

    del df
    log_memory_usage(label=f"After deletion of df")
    # Count total rsv_specific cases in 2023 for sense check
    if config["set"] == "resp":
        print(
            column_total_check(
                measures_dict[subgroup][-1],
                column="numerator",
                year=2023,
                measure_name="rsv_specific",
            )
        )

# Apply pre-processing to each subgroup dataframe
for subgroup in config["subgroups"]:

    # Save Concatenate yearly intervals into a single dataframe
    measures_dict[subgroup] = pd.concat(measures_dict[subgroup])

    print(f"Data types of input: {measures_dict[subgroup].dtypes}", flush=True)
    log_memory_usage(label=f"After deletion of dataframes")
    # Count total rsv_specific cases in 2023 for sense check
    if config["set"] == "resp":
        print(
            column_total_check(
                measures_dict[subgroup],
                column="numerator",
                year=2023,
                measure_name="rsv_specific",
            )
        )

    if subgroup == "rur_urb_class":
        # Replace numerical values with string values
        measures_dict[subgroup] = replace_nums(
            measures_dict[subgroup], replace_ethnicity=False, replace_rur_urb=True
        )

    if subgroup == "ethnicity":
        # Replace numerical values with string values
        measures_dict[subgroup] = replace_nums(
            measures_dict[subgroup], replace_ethnicity=True, replace_rur_urb=False
        )

    if config["test"]:
        np.random.seed(42)  # For reproducibility in testing
        # Increase numerator and list_size for testing of downstream functions
        measures_dict[subgroup]["numerator"] = np.random.randint(
            0, 500, size=len(measures_dict[subgroup])
        )
        measures_dict[subgroup]["list_size"] = np.random.randint(
            500, 1000, size=len(measures_dict[subgroup])
        )

        # Simulate extra data for downstream testing
        print(measures_dict[subgroup]["interval_start"].unique())
        print("Simulating practice measures data for testing")

        # Define number of repeats and time delta based on yearly or weekly config
        if config["yearly"]:
            n_intervals = 3 
            time_delta_weeks = 52  # 1 year gap between intervals
        else:
            n_intervals = 52 * 3  # 3 years ("2023-05-08" - ""2026-05-08")
            time_delta_weeks = 1  # 1 week gap between intervals

        # Generate extended rows by shifting weeks and randomizing values
        extended_rows = []
        for i in range(1, n_intervals + 1):
            df_copy = measures_dict[subgroup].copy()
            df_copy["interval_start"] = df_copy["interval_start"] + timedelta(
                weeks=time_delta_weeks * i
            )
            df_copy["numerator"] = np.random.randint(0, 500, size=len(df_copy))
            df_copy["list_size"] = np.random.randint(500, 1000, size=len(df_copy))
            extended_rows.append(df_copy)

        # Combine original and simulated rows
        measures_dict[subgroup] = pd.concat(
            [measures_dict[subgroup]] + extended_rows, ignore_index=True
        )

        # Sample 10 unique practice_pseudo_ids
        test_practices = pd.Series(
            measures_dict[subgroup]["practice_pseudo_id"].unique()
        ).sample(10)
        measures_dict[subgroup] = measures_dict[subgroup][
            measures_dict[subgroup]["practice_pseudo_id"].isin(test_practices)
        ]

        # Set values in 'numerator' column to 0 for the selected rows to simulate real data missingness
        # Define mask for conditional rows
        mask = (measures_dict[subgroup]["measure"] == "online_consult") & (
            measures_dict[subgroup]["interval_start"] < "2016-11-30"
        )
        # Get indices that meet condition
        matching_indices = measures_dict[subgroup][mask].index
        measures_dict[subgroup].loc[matching_indices, "numerator"] = 0

        # Drop some rows to simulate real data missingness
        # Define mask for conditional rows
        mask = (measures_dict[subgroup]["measure"] == "call_from_gp") & (
            measures_dict[subgroup]["interval_start"] < "2016-11-30"
        )
        # Get indices that meet condition
        matching_indices = measures_dict[subgroup][mask].index
        # Drop rows
        measures_dict[subgroup] = measures_dict[subgroup].drop(matching_indices)
        # Drop duplicates
        measures_dict[subgroup] = pd.concat(
            [measures_dict[subgroup]] + extended_rows, ignore_index=True
        )
        measures_dict[subgroup] = measures_dict[subgroup].drop_duplicates(
            subset=["practice_pseudo_id", "measure", "interval_start"]
        )

        # Modify rsv and flu specific to be sparse to simulate real data
        measures_dict[subgroup]["numerator"] = np.where(
            measures_dict[subgroup]["measure"].isin(["rsv_specific", "flu_specific"]),
            np.random.choice([0, 1], size=len(measures_dict[subgroup]), p=[0.95, 0.05]),
            measures_dict[subgroup]["numerator"],
        )

        # Delete some practices from 2023 only to simiulate new practices joining over time
        practices_2023 = measures_dict[subgroup][
            measures_dict[subgroup]["interval_start"] < "2023-12-12"
        ]["practice_pseudo_id"].unique()
        practices_to_drop = np.random.choice(
            practices_2023, size=int(0.2 * len(practices_2023)), replace=False
        )
        # Remove these practices from the entire 2023 comparison group (up to May 2024)
        measures_dict[subgroup] = measures_dict[subgroup][
            ~(
                (measures_dict[subgroup]["practice_pseudo_id"].isin(practices_to_drop))
                & (measures_dict[subgroup]["interval_start"] <= "2024-06-01")
            )
        ]


    # Remove intervals before the first summer reference period
    measures_dict[subgroup] = measures_dict[subgroup][
        measures_dict[subgroup]["interval_start"] > "2016-05-31"
    ]

    # Remove practices with < 750 list size
    if config["practice_measures"]:
        print(
            f"Number of practices before filtering: {measures_dict[subgroup]['practice_pseudo_id'].nunique()}",
            flush=True,
        )
        measures_dict[subgroup] = measures_dict[subgroup][
            (measures_dict[subgroup]["list_size"] > 750)
        ]
        print(
            f"Number of practices after filtering: {measures_dict[subgroup]['practice_pseudo_id'].nunique()}",
            flush=True,
        )

    # Count total rsv_specific cases in 2023 for sense check
    if config["set"] == "resp":
        print(
            column_total_check(
                measures_dict[subgroup],
                column="numerator",
                year=2023,
                measure_name="rsv_specific",
            )
        )

    # MOVE DOWNSTREAM
    # measures_dict[subgroup][["numerator_midpoint6", "list_size_midpoint6"]] = roundmid_any(measures_dict[subgroup][["numerator", "list_size"]], to=6)

    # Count total rsv_specific cases in 2023 for sense check
    if config["set"] == "resp":
        print(
            column_total_check(
                measures_dict[subgroup],
                column="numerator",
                year=2023,
                measure_name="rsv_specific",
            )
        )

    # Ensure correct datetime format
    measures_dict[subgroup]["interval_start"] = pd.to_datetime(
        measures_dict[subgroup]["interval_start"]
    ).dt.tz_localize(None)
    measures_dict[subgroup]["month"] = measures_dict[subgroup][
        "interval_start"
    ].dt.month
    # If Jan - May, RR is relative to prev years summer. If June - Dec, RR is relative to same years summer.
    measures_dict[subgroup]["summer_year"] = np.where(
        measures_dict[subgroup]["month"] <= 5,
        measures_dict[subgroup]["interval_start"].dt.year - 1,
        measures_dict[subgroup]["interval_start"].dt.year,
    )

    # Calculate rate per 1000
    measures_dict[subgroup]["Rate_per_1000"] = (
        measures_dict[subgroup]["numerator"]
        / measures_dict[subgroup]["list_size"]
        * 1000
    )

    # Define pandemic dates
    if config["test"]:
        pandemic_start = pd.to_datetime(config["test_config"]["pandemic_start"])
        pandemic_end = pd.to_datetime(config["test_config"]["pandemic_end"])
    else:
        pandemic_start = pd.to_datetime(config["pandemic_start"])
        pandemic_end = pd.to_datetime(config["pandemic_end"])
    pandemic_conditions = [
        measures_dict[subgroup]["interval_start"] < pd.to_datetime(pandemic_start),
        (measures_dict[subgroup]["interval_start"] >= pd.to_datetime(pandemic_start))
        & (measures_dict[subgroup]["interval_start"] <= pd.to_datetime(pandemic_end)),
        measures_dict[subgroup]["interval_start"] > pd.to_datetime(pandemic_end),
    ]
    choices = ["Before", "During", "After"]
    measures_dict[subgroup]["pandemic"] = np.select(pandemic_conditions, choices)
    log_memory_usage(
        label=f"Final memory usage"
    )  # test is 10 times higher for practice_subgroups

    # Save processed file
    if config["practice_subgroup_measures"]:
        output_path_subgroup = output_path + f"_{subgroup}"
    elif config["practice_measures"]:
        output_path_subgroup = output_path

    # Count total rsv_specific cases in 2023 for sense check
    if config["set"] == "resp":
        print(
            column_total_check(
                measures_dict[subgroup],
                column="numerator",
                year=2023,
                measure_name="rsv_specific",
            )
        )

    read_write(
        read_or_write="write",
        path=output_path_subgroup,
        df=measures_dict[subgroup],
        file_type="arrow",
    )
    del measures_dict[subgroup]  # Delete dataframe to save memory
    log_memory_usage(label=f"After saving and deleting {subgroup} dataframe")
