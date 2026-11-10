# This script generate the table one statistics (demographic breakdowns)
# Uses the denominator from the seen_in_interval measure
# Takes characteristics at a specific timepoint (April 2016)

# Options
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --appt restricts measures to those with an appointment in interval
# USAGE: python analysis/freq_table.py
# Depends on pre_processing.py

import pandas as pd
from utils import *
import pyarrow.feather as feather
from parse_args import *
import numpy as np
from pathlib import Path

#  ---------------  Configuration -----------------------------------------------------
# Use June 6th (earlier dates may have been filtered out)
TABLE_ONE_DATE = datetime.strptime("2016-06-06", "%Y-%m-%d")

if not config["practice_subgroup_measures"]:
    raise ValueError(
        "This script is only for practice subgroup measures. Please use --practice_subgroup_measures"
    )

if config["test"]:
    # Use test start date to avoid loading all the way back to 2016 for testing
    date = datetime.strptime(config["test_config"]["start_date"], "%Y-%m-%d")
else:
    date = TABLE_ONE_DATE

# ---------------  Load and format data ----------------------------------------------

# Load and format data for each interval
print(f"Loading {config['group']} measures {date}", flush=True)
base_dir = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}"
output_path = f"{base_dir}/freq_table_{config['group']}"
last_interval_output_path = output_path + "_last_interval"

patient_df_dict = {}
for subgroup in config["subgroups"]:

    input_path = f"{base_dir}/proc_{config['group']}_measures_{subgroup}"
    patient_df_dict[subgroup] = read_write("read", input_path)

# Combine the practice-level rows for all subgroup measures. The national
# subgroup totals are produced below by summing across these practice rows.
patient_df = pd.concat(patient_df_dict.values(), ignore_index=True)

# Keep only the seen-in-interval measure rows used for table one.
patient_df = patient_df[
    (patient_df["measure"].str.contains("seen_in_interval"))
    & ~(patient_df["measure"].str.contains("practice_pseudo_id|stp"))
]

table_subgroups = [subgroup for subgroup in config["subgroups"] if subgroup != "stp"]

if config["test"]:
    output_path = output_path + "_test"
    last_interval_output_path = last_interval_output_path + "_test"


def create_frequency_table(patient_df, interval_start, output_path, check_total=False):
    """
    Create a frequency table for the given interval.
    """
    interval_df = patient_df[patient_df["interval_start"] == interval_start]

    table_one = {}
    
    for var in table_subgroups:
        # Use the seen_in_interval measure for the variable to get the counts and proportions
        var_df = interval_df[interval_df["measure"] == f"seen_in_interval_{var}"]

        # Create one indicator column per subgroup level and weight each
        # practice by its list size. Summing across practices therefore gives
        # the national list size for each subgroup level.
        table_one[var] = (
            pd.get_dummies(var_df[var])
            .multiply(var_df["list_size"], axis=0)
            .sum()
            .reset_index()
        )
        table_one[var].columns = ["level", "count"]

        # Apply midpoint-6 rounding after practice list sizes have been
        # summed, rather than rounding each practice contribution first.
        table_one[var] = roundmid_any(table_one[var], ["count"], to=6)

        # Calculate proportions from the rounded national subgroup totals.
        table_one[var]["prop"] = (
            table_one[var]["count_mp6"] / table_one[var]["count_mp6"].sum()
        )

    # Format the table one dataframes into a single dataframe 
    formatted_list = []
    for key, df in table_one.items():
        df["Category"] = key
        formatted_list.append(df[["Category", "level", "count_mp6", "prop"]])
    result_df = pd.concat(formatted_list, axis=0, ignore_index=True)
    result_df["prop"] = result_df["prop"] * 100

    # Add a total row for each category from the rounded national subgroup
    # counts shown in the table.
    total_row = (
        result_df.groupby("Category")
        .agg({"count_mp6": "sum", "prop": "sum"})
        .reset_index()
    )
    result_df = pd.concat([result_df, total_row.assign(level="Total")], ignore_index=True)

    # Add practice rows - use the seen_in_interval_sex measure to get the number of practices before and after the list size filter
    # because it is guaranteed to be present in all datasets
    sex_df = interval_df[interval_df["measure"] == "seen_in_interval_sex"]
    n_practices_before_filter = sex_df[
        "n_practices_pre_list_size_filter"
    ].iloc[0]
    n_practices_after_filter = sex_df[
        "n_practices_post_list_size_filter"
    ].iloc[0]
    practice_rows = pd.DataFrame(
        {
            "Category": ["n_practices", "n_practices"],
            "level": ["pre_list_size_filter", "post_list_size_filter"],
            "count_mp6": [n_practices_before_filter, n_practices_after_filter],
            "prop": [np.nan, np.nan],
        }
    )
    # Add practice rows to the result dataframe
    result_df = pd.concat([result_df, practice_rows], ignore_index=True)
    result_df.rename(columns={"prop": "prop_mp6_derived"}, inplace=True)

    # Add a check to ensure that the total list size for seen_in_interval_sex matches the expected value
    if check_total:
        total_list_size = table_one["sex"]["count_mp6"].sum()
        test_total_list_size = result_df[
            (result_df["Category"] == "sex") & (result_df["level"] == "Total")
        ]["count_mp6"].iloc[0]
        assert total_list_size == test_total_list_size, (
            "Total list size for seen_in_interval_sex does not match expected value. "
            f"Expected: {total_list_size}, Got: {test_total_list_size}"
        )

    result_df.round(3).to_csv(output_path + ".csv", index=False)


create_frequency_table(patient_df, date, output_path, check_total=config["test"])

last_interval = patient_df["interval_start"].max()
create_frequency_table(
    patient_df,
    last_interval,
    last_interval_output_path,
)
