# This script sense checks test jobs by aggregating up to national level
# to see if the measures worked (produced non-zero totals).
# Not used as part of the actual deployment pipeline.

import pandas as pd
from utils import *
import pyarrow.feather as feather
from parse_args import *
import numpy as np

# Load and format data for each interval
print(f"Loading {config['group']} measures {config['test_config']['start_date']}", flush=True)
input_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/{config['group']}_measures_{config['test_config']['start_date']}"
output_path = f"output/{config['group']}_measures_{config['set']}{config['appt_suffix']}{config['agg_suffix']}/sense_check_{config['group']}_{config['test_config']['start_date']}"
df = read_write(read_or_write="read", path=input_path)

# Aggregate data to national level
df = df.groupby(["measure", "interval_start"]).agg({"numerator": ["sum"], "denominator": ["sum"]})
# Flatten column headings
df.columns = df.columns.get_level_values(0)
df['ratio'] = (df['numerator'] / df['denominator'])*100000
read_write(read_or_write="write", path=output_path, file_type="csv", df=df)
