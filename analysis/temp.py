
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
# python analysis/temp.py --test --set resp --practice_measures

# --------- Configuration ------------------------------------------------

dates = generate_annual_dates(config["study_end_date"], config["n_years"])

print(dates)
date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]

if config["test"]:

    # For testing, use only one date
    dates = [config["test_config"]["start_date"]]

output_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/proc_{config['group']}_measures"
proc_df = read_write(read_or_write="read", path=output_path, file_type="dict")
log_memory_usage(label="Before loading data")

# practice measures = 201 mb
# practice subgroup measures dataframe = 473 mb
# practice subgroup measures dict = 287 mb
# Thus, saving as dictionary with trimmed columns is more memory efficient for practice subgroup measures


