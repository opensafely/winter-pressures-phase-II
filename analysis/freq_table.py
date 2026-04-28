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

patient_df_dict = {}
for subgroup in config["subgroups"]:

    input_path = f"{base_dir}/proc_{config['group']}_measures_{subgroup}"
    patient_df_dict[subgroup] = read_write("read", input_path)

patient_df = pd.concat(patient_df_dict.values(), ignore_index=True)

# 1. Extract first week of data
# 2. Use seen_in_interval denominator, which will capture registered patients from all practices that had at least one appt per week
# 3. Drop practice IDs and STPs as we can't release for discolosure control
target_iso = date.isocalendar()
interval_iso = patient_df["interval_start"].dt.isocalendar()
patient_df = patient_df[
    (interval_iso.year == target_iso[0])
    & (interval_iso.week == target_iso[1])
    & (patient_df["measure"].str.contains("seen_in_interval"))
    & ~(patient_df["measure"].str.contains("practice_pseudo_id|stp"))
]
patient_df.rename(columns={"denominator": "list_size"}, inplace=True)
patient_df.drop(columns=["practice_pseudo_id", "stp"], inplace=True)
config["subgroups"].remove("stp")

if config["test"]:
    # Increase numerator and list_size for testing of downstream functions
    patient_df["numerator"] = np.random.randint(0, 1000, size=len(patient_df))
    patient_df["list_size"] = np.random.randint(1000, 2000, size=len(patient_df))
    output_path = output_path + "_test"

    #  ------------ Test Cases ---------------------------------------------

    # 1 - Total list size check for seen_in_interval_sex
    total_list_size = patient_df[patient_df["measure"] == "seen_in_interval_sex"][
        "list_size"
    ].sum()

# ---------------  Create frequency table -----------------------------------------------

table_one = {}
# Iterate over all the demographic variables we want in table one
for var in config["subgroups"]:
    # Create an binary matrix composed of indicator variables representing the categorical value for each group (e.g. cols ethnicity_black: 0, ethnicity_white: 1)
    # Multiply this matrix by the vector of list_sizes representing the size of the given group
    # Sum to get the total denominator value from all the groups (Sum(Categories x list_size))
    # e.g. (e.g. cols ethnicity_black: 0, ethnicity_white: 1, list_size: 500) -> 1 X 500 -> level: white, count: 500
    table_one[var] = (
        pd.get_dummies(patient_df[var])
        .multiply(patient_df["list_size"], axis=0)
        .sum()
        .reset_index()
    )
    table_one[var].columns = ["level", "count"]
    # Round values
    table_one[var]["count"] = roundmid_any(table_one[var]["count"], to=6)
    table_one[var]["prop"] = table_one[var]["count"] / table_one[var]["count"].sum()

# Initialize an empty list to hold formatted DataFrames
formatted_list = []

# Loop over each item in the dictionary
for key, df in table_one.items():
    # Add a column for the category (e.g., age, sex, ethnicity)
    df["Category"] = key
    # Append the DataFrame to the list
    formatted_list.append(df[["Category", "level", "count", "prop"]])

# Concatenate all DataFrames into one
result_df = pd.concat(formatted_list, axis=0, ignore_index=True)
result_df["prop"] = (result_df["prop"]) * 100

# Add total row for each category
total_row = (
    result_df.groupby("Category").agg({"count": "sum", "prop": "sum"}).reset_index()
)
# Merge total row with the original DataFrame
result_df = pd.concat([result_df, total_row.assign(level="Total")], ignore_index=True)

# Rename cols
result_df.rename(
    columns={
        "count": "count_mp6",
        "prop": "prop_mp6_derived",
        "total": "total_mp6_derived",
    },
    inplace=True,
)

# ------------- Test case check ----------------------------

if config["test"]:
    # 1 - Total list size check for seen_in_interval_sex
    test_total_list_size = result_df[
        (result_df["Category"] == "sex") & (result_df["level"] == "Total")
    ]["count_mp6"].iloc[0]
    assert (
        total_list_size == test_total_list_size
    ), f"Total list size for seen_in_interval_sex does not match expected value. Expected: {total_list_size}, Got: {test_total_list_size}"

result_df = result_df.round(3)

# Save processed file
result_df.to_csv(output_path + ".csv", index=False)
