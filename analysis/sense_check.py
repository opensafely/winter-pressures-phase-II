# This script sense checks test jobs by aggregating up to national level
# to see if the measures worked (produced non-zero totals).
# Not used as part of the actual deployment pipeline.

import pandas as pd
from utils import *
import pyarrow.feather as feather
from wp_config_setup import *
import numpy as np

# Load and format data for each interval
print(f"Loading {args.group} measures {args.test_start_date}", flush=True)
input_path = f"output/{args.group}_measures_{args.set}{args.appt_suffix}/{args.group}_measures_{args.test_start_date}"
output_path = f"output/{args.group}_measures_{args.set}{args.appt_suffix}/sense_check_{args.group}_{args.test_start_date}"
df = read_write(read_or_write="read", path=input_path)

# Aggregate data to national level
df = df.groupby(["measure", "interval_start"]).agg({"numerator": ["sum"], "denominator": ["sum"]})
# Flatten column headings
df.columns = df.columns.get_level_values(0)
df['ratio'] = (df['numerator'] / df['denominator'])*100000
read_write(read_or_write="write", path=output_path, file_type="csv", df=df)
