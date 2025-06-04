import pandas as pd
from utils import *
import pyarrow.feather as feather
from wp_config_setup import *
import numpy as np

if args.test:
    dates = generate_annual_dates(args.study_end_date, args.n_years)
    date = dates[0]  
else:
    date = '2020-04-06'

# Load and format data for each interval
print(f"Loading {args.group} measures {date}", flush=True)
input_path = f"output/{args.group}_measures/{args.group}_measures_{date}"
output_path = f"output/{args.group}_measures/freq_table_{args.group}"

patient_df = read_write(read_or_write = 'read', path = input_path, 
                    dtype=args.dtype_dict, true_values=["T"], false_values=["F"])

# Extract first week of data
patient_df = patient_df[(patient_df['interval_start'].astype(str) == dates[0]) & 
                        (patient_df['measure'] == 'seen_in_interval')]
patient_df.rename(columns={'denominator': 'list_size'}, inplace=True)

if args.test:
    # Increase numerator and list_size for testing of downstream functions
    patient_df['numerator'] = np.random.randint(0, 1000, size = len(patient_df))
    patient_df['list_size'] = np.random.randint(1000, 2000, size = len(patient_df))
    output_path = output_path + '_test'

if args.demograph_measures:
    # Replace numerical values with string values
    patient_df = replace_nums(patient_df, replace_ethnicity=True, replace_rur_urb=True)

# Extract demographic variables
excluded_cols = ['numerator', 'list_size', 'measure', 'interval_start', 'interval_end', 'ratio']
table_one_vars = [col for col in patient_df.columns if col not in excluded_cols]
table_one = {}
# Iterate over all the demographic variables we want in table one
for var in table_one_vars:
    # Create an binary matrix composed of indicator variables representing the categorical value for each group (e.g. cols ethnicity_black: 0, ethnicity_white: 1)
    # Multiply this matrix by the vector of list_sizes representing the size of the given group
    # Sum to get the total denominator value from all the groups (Sum(Categories x list_size))
    # e.g. (e.g. cols ethnicity_black: 0, ethnicity_white: 1, list_size: 500) -> 1 X 500 -> level: white, count: 500
    table_one[var] = pd.get_dummies(patient_df[var]).multiply(patient_df['list_size'], axis=0).sum().reset_index()
    table_one[var].columns = ['level', 'count']
    table_one[var]['prop'] = table_one[var]['count']/table_one[var]['count'].sum()

# Initialize an empty list to hold formatted DataFrames
formatted_list = []

# Loop over each item in the dictionary
for key, df in table_one.items():
    # Add a column for the category (e.g., age, sex, ethnicity)
    df['Category'] = key
    # Append the DataFrame to the list
    formatted_list.append(df[['Category', 'level', 'count', 'prop']])

# Concatenate all DataFrames into one
result_df = pd.concat(formatted_list, axis=0, ignore_index=True)
result_df['prop'] = ((result_df['prop'])*100)

# Add total row for each category
total_row = result_df.groupby('Category').agg({'count': 'sum', 'prop': 'sum'}).reset_index()
# Merge total row with the original DataFrame
result_df = pd.concat([result_df, total_row.assign(level='Total')], ignore_index=True)
result_df = result_df.round(3)

# Save processed file
result_df.to_csv(output_path + '.csv', index=False)