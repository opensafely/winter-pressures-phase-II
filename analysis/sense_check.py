# This script sense checks test jobs by aggregating up to national level
# to see if the measures worked (produced non-zero totals).
# Not used as part of the actual deployment pipeline.

import pandas as pd
from utils import *
import pyarrow.feather as feather
from wp_config_setup import *
import numpy as np

if args.test:
    year = '2016'
else:
    year = '2020'

dates = generate_annual_dates(args.study_end_date, args.n_years)
date = [date for date in dates if date.startswith(year)][0]

# Load and format data for each interval
print(f"Loading {args.group} measures {date}", flush=True)
input_path = f"output/{args.group}_measures_{args.set}/{args.group}_measures_{date}"
output_path = f"output/{args.group}_measures_{args.set}/sense_check_{args.group}"
df = read_write(read_or_write = 'read', path = input_path)

# Aggregate data to national level
df = df.groupby(["measure"]).agg({"numerator": ["sum"], "denominator": ["sum"]})
# Flatten column headings
df.columns = df.columns.get_level_values(0)
read_write(read_or_write = 'write', path = output_path, file_type = 'csv', df = df)