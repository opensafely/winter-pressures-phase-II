# Load decile table for seen_in_interval measure
# Seperate bottom 30%, 20, 10% of practices
# Calcualte yearly demographics of each set of practices
# e.g. top 70% age, region, stp; bottoom 30% age, region...; bottom 20% age, region...; bottom 10% age, region...

# analysis/analyse_low_appts.py
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

# -------- Load data ----------------------------------

# Generate dates
dates = generate_annual_dates(config["study_end_date"], config["n_years"])
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

log_memory_usage(label="Before loading data")

input_path = (
    f"output/{config['group']}_measures_{config['set']}/proc_{config['group']}_measures_midpoint6"
)
practice_interval_df = read_write("read", input_path)
breakpoint()
log_memory_usage(label="After loading data")