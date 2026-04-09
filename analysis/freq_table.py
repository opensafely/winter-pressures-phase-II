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

if not config["practice_subgroup_measures"]:
    raise ValueError("This script is only for practice subgroup measures. Please use --practice_subgroup_measures")

if config["test"]:
    # Use explicit test interval start for lightweight test snapshots.
    date = config["test_config"]["start_date"]
else:
    dates = generate_annual_dates(config["study_end_date"], config["n_years"])
    date = "2020-04-06"
    matching_dates = [d for d in dates if d.startswith("2016")]
    if matching_dates:
        date = matching_dates[0]

# ---------------  Load and format data ----------------------------------------------

# Load and format data for each interval
print(f"Loading {config['group']} measures {date}", flush=True)
base_dir = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}"

patient_df_dict = {}
for subgroup in config["subgroups"]:

    input_path = f"{base_dir}/proc_{config['group']}_measures_{subgroup}"
    output_path = f"{base_dir}/freq_table_{config['group']}"

    patient_df_dict[subgroup] = read_write("read", input_path)

patient_df = pd.concat(patient_df_dict.values(), ignore_index=True)

# 1. Extract first week of data
# 2. Use seen_in_interval denominator, which will capture registered patients from all practices that had at least one appt per week
# 3. Drop practice IDs and STPs as we can't release for discolosure control
patient_df = patient_df[
    (patient_df["interval_start"].astype(str) == date)
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
result_df = result_df.round(3)

# Save processed file
result_df.to_csv(output_path + ".csv", index=False)
