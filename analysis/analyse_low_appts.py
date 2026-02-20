# Load decile table for seen_in_interval measure
# Seperate bottom 30%, 20, 10% of practices
# Calcualte yearly demographics of each set of practices
# e.g. top 70% age, region, stp; bottoom 30% age, region...; bottom 20% age, region...; bottom 10% age, region...

# python analysis/analyse_low_appts.py
# Options
# --practice_measures/practice_subgroup_measures to choose which type of measures to process
# --test uses test data
# --set specifies the measure set (appts_table, sro, resp)
# --released uses already released data
# --appt restricts measures to those with an appointment in interval
# --weekly_agg aggregates weekly intervals to yearly

import pandas as pd
from utils import *
import pyarrow.feather as feather
from parse_args import *
import numpy as np
import random
from datetime import datetime, timedelta
from scipy import stats
from itertools import product
import pyarrow.feather as feather
from itertools import combinations
from scipy.stats import pearsonr, spearmanr
import glob

# -------- Load data ----------------------------------

# Generate dates
dates = generate_annual_dates(config["study_end_date"], config["n_years"])
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

log_memory_usage(label="Before loading data")

# List all measure-specific files
input_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/proc_{config['group']}_measures_midpoint6"
practice_interval_dict = read_write("read", input_path, file_type="pickle")

# ------------- Pre-processing --------------------------------

for subgroup in practice_interval_dict.keys():

    # Only need seen_in_interval
    practice_interval_dict[subgroup] = practice_interval_dict[subgroup][practice_interval_dict[subgroup]['measure'].str.contains('seen_in_interval')]
    # Remove non-sex categories from the measure column
    practice_interval_dict[subgroup]['measure'] = practice_interval_dict[subgroup]['measure'].cat.remove_unused_categories()
    # Aggregate weeks to years
    practice_interval_dict[subgroup]["year"] = practice_interval_dict[subgroup]["interval_start"].dt.year

# ------------- Calculate ranks of practices -------------------------

# Use sex as measure for practice-level aggregation as its required in inclusion criteria
practice_interval_df = practice_interval_dict['sex']
practice_agg_df = practice_interval_df.groupby(["practice_pseudo_id", "measure", "year"]).agg({"numerator_midpoint6": "sum", "list_size_midpoint6": "sum"}).reset_index()
# Calculate rate per 1000
practice_agg_df["rate_per_1000"] = (practice_agg_df["numerator_midpoint6"] / practice_agg_df["list_size_midpoint6"])*1000
# Calculate percentile position for each practice
practice_agg_df["percentile"] = practice_agg_df.groupby("measure")["rate_per_1000"].rank(pct=True)*100
# Extract bottom 20% of practices for each measure
practice_agg_df["bottom_20pct"] = practice_agg_df["percentile"] <= 20

# -------------- Calcculate demographics of practices ----------------

# Iterate through each subgroup

for subgroup in practice_interval_dict.keys():

    # Merge low_appt identifier into each subgroup-specific dataframe
    practice_interval_dict[subgroup] = practice_interval_dict[subgroup].merge(practice_agg_df[['practice_pseudo_id', 
                                                                                               'bottom_20pct']], on="practice_pseudo_id", how="left")
    # Select columns to aggregate
    cols_to_agg = [col for col in practice_interval_dict[subgroup].columns if col not in ['interval_start', 'numerator_midpoint6',
                                                                                          'rate_per_1000_midpoint6_derived', 'list_size_midpoint6', 
                                                                                          'practice_pseudo_id', 'measure']]
    # Find total list size per year-bottom_20pct combo
    total_list_size = practice_interval_dict[subgroup].groupby(["bottom_20pct", "year"])["list_size_midpoint6"].sum().reset_index().rename(columns={"list_size_midpoint6": "total_list_size"})
    # Groupby low_appt identifier and aggregate list size sums
    practice_interval_dict[subgroup] = practice_interval_dict[subgroup].groupby(cols_to_agg).agg({"list_size_midpoint6": "sum"}).reset_index().rename(columns={"list_size_midpoint6": "list_size"})

    # Merge total list size back in to calculate percentage of list size in each demographic group
    practice_interval_dict[subgroup] = practice_interval_dict[subgroup].merge(total_list_size, on=["bottom_20pct", "year"], how="left")
    practice_interval_dict[subgroup]["pct_list_size"] = round((practice_interval_dict[subgroup]["list_size"] / practice_interval_dict[subgroup]["total_list_size"])*100, 2)
    # Sort by bottom_20pct, year
    practice_interval_dict[subgroup] = practice_interval_dict[subgroup].sort_values(by=["bottom_20pct", "year"])
    
    # Move bottom_20pct, year to start
    bottom_20pct_col = practice_interval_dict[subgroup].pop('bottom_20pct')
    year_col = practice_interval_dict[subgroup].pop('year')
    practice_interval_dict[subgroup].insert(0, 'bottom_20pct', bottom_20pct_col)
    practice_interval_dict[subgroup].insert(1, 'year', year_col)

# Merge summaries for each subgroup into one dataframe
demographics_df = pd.concat(practice_interval_dict.values(), axis=0, ignore_index=True)

# Output to CSV
output_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/{config['group']}_measures_demographics"
read_write("write", output_path, df=demographics_df, file_type="csv")
