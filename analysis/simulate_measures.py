# This script generates simulated measures data for testing purposes, 
# since dummy data of sufficient size takes a long time to generate.
# Option --comorbid_measures flag to aggregate by comorbidities
# Option --demograph_measures flag to aggregate by demographics
# Option --practice_measures flag to aggregate by practice

import pandas as pd
import numpy as np
from wp_config_setup import args
from utils import *

# Simulate a small dataset
dates = generate_annual_dates(args.study_end_date, args.n_years)
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]
output_path = f"output/{args.group}_measures/{args.group}_measures_{dates[0]}"
study_start_date = date_objects[0]

# Generate 4 years worth of data (pre, during, and post-pandemic covered)
dates = pd.date_range(start=study_start_date, periods=(52*4), freq='7D').strftime('%Y-%m-%d')  

# Save as Arrow file (Parquet or Feather)
df = simulate_dataframe(args.dtype_dict, nrows = len(dates))
read_write('write', output_path, df = df)