#TODO:
# 1. Check assumptions for poissoin
# 2. Add visualisation of them to deciles_chart.r

import pandas as pd
from utils import generate_annual_dates, log_memory_usage, replace_nums
import pyarrow.feather as feather
from wp_config_setup import *
import numpy as np
import random
from datetime import datetime, timedelta
from scipy import stats

# -------- Set up variables ----------------------------------

if test == True:
    study_start_date = datetime.strptime("2019-08-10", "%Y-%m-%d")
    suffix = "_test"
else:
    dates = generate_annual_dates(2016, '2024-07-31')
    suffix = ""
    study_start_date = dates[0]

def normalize_by_summer(row, max_year, min_year, max_year_issue, min_year_issue):
    year = row['year']
    # Check if the year is the max or min year and if it has a summer
    if (year == max_year) and (max_year_issue):
        print(f'Interval {row.interval_start} does not have a summer for that year, using prev years')
        year = year - 1
    elif (year == min_year) and (min_year_issue):
        print(f'Interval {row.interval_start} does not have a summer for that year, using next years')
        year = year + 1
    else:
        print(f'Interval {row.interval_start} has a summer for that year')
    # Get the summer value for the measure and year
    summer_value = season_df.loc[(row['measure'], 'Jun-Jul', year)]['mean']
    # Calculate rate normalized by summer baseline
    return row.rate_per_1000 / summer_value

# Function to test difference between stand_summer and raw values
def test_difference(row):
    # Get the group for the measure, season, and year
    print(f"Testing difference for measure: {row['measure']}, season: {row['season']}, year: {row['year']}")
    # get first row of seasonality_df
    #row = seasonality_df.iloc[0]
    summer = practice_df[
        (practice_df['measure'] == row['measure'][0]) &
        (practice_df['season'] == 'Jun-Jul') &
        (practice_df['year'] == row['year'][0])
    ]
    season = practice_df[
        (practice_df['measure'] == row['measure'][0]) &
        (practice_df['season'] == row['season'][0]) &
        (practice_df['year'] == row['year'][0])
    ]
    # Get the summer values and the winter values
    vals_summer = summer['rate_per_1000']
    vals_season = season['rate_per_1000']
    
    # Conduct poisson test
    count1 = round(vals_summer.sum())
    exposure1 = len(vals_summer)
    print(f"Count summer: {count1}, Exposure summer: {exposure1}")
    count2 = round(vals_season.sum())
    exposure2 = len(vals_season)
    print(f"Count season: {count2}, Exposure season: {exposure2}")
    if count1 == 0 or count2 == 0:
        print("One of the counts is zero, returning NaN")
        return np.nan
    result = stats.poisson_means_test(count1, exposure1, count2, exposure2, alternative='two-sided')

    # Get the p-value
    pval = result.pvalue

    # Return significance at p < 0.05
    return round(pval, 4)

# Map months to winter parts
def get_season(month):
    if month in [9, 10]:
        return 'Sep-Oct'
    elif month in [11, 12]:
        return 'Nov-Dec'
    elif month in [1, 2]:
        return 'Jan-Feb'
    elif month in [6, 7]:
        return 'Jun-Jul'
    else:
        return None  # Exclude non-winter months

log_memory_usage(label="Before loading data")

# -------- Practice measures processing ----------------------------------

# Load practice data
if test:
    # Generate simulated data
    # Parameters
    measures = ['CancelledbyPatient', 'CancelledbyUnit', 'DidNotAttend',
       'GP_ooh_admin', 'Waiting', 'call_from_gp', 'call_from_patient',
       'emergency_care', 'follow_up_app', 'online_consult',
       'secondary_referral', 'seen_in_interval', 'start_in_interval',
       'tele_consult', 'vax_app', 'vax_app_covid', 'vax_app_flu']

    # Define sample values
    practice_ids = range(1, 3)  # 3 practices
    # Generate 4 years worth of data (pre, during, and post-pandemic covered)
    dates = pd.date_range(start=study_start_date, periods=(52*4), freq='7D').strftime('%Y-%m-%d')  

    # Initialize list to collect rows
    rows = []

    # Iterative data generation
    for measure in measures:
        for practice_id in practice_ids:
            for i, date in enumerate(dates):
                rows.append({
                    'Unnamed: 0': 1,
                    'measure': measure,
                    'interval_start': date,
                    'practice_pseudo_id': practice_id,
                    'numerator': np.round(np.random.uniform(0, 50), 1),  # float64
                    'list_size': np.round(np.random.uniform(100, 1000), 1)  # float64
                })
        # Convert to DataFrame
    practice_df = pd.DataFrame(rows)
else:
    practice_df = feather.read_feather("output/practice_measures/proc_practice_measures.arrow")

# -------- Normalize counts ----------------------------------

# Ensure interval_start is datetime
practice_df['interval_start'] = pd.to_datetime(practice_df['interval_start'])
# Extract year
practice_df['year'] = practice_df['interval_start'].dt.year
practice_df['month'] = practice_df['interval_start'].dt.month
practice_df['rate_per_1000'] = practice_df['numerator'] / practice_df['list_size'] * 1000
pandemic_conditions = [
    practice_df['interval_start'] < pd.to_datetime("2020-03-01"),
        (practice_df['interval_start'] >= pd.to_datetime("2020-03-01")) & 
        (practice_df['interval_start'] <= pd.to_datetime("2021-03-17")),
    practice_df['interval_start'] > pd.to_datetime("2021-03-17")
]
choices = ['pre', 'during', 'post'] 
practice_df['pandemic'] = np.select(pandemic_conditions, choices)

# Remove interval containing xmas shutdown
practice_df = practice_df.loc[~(
                                (practice_df['interval_start'].dt.month == 12) & 
                                    (
                                    (practice_df['interval_start'].dt.day >= 19) &
                                    (practice_df['interval_start'].dt.day <= 26)
                                    )
                                )
                            ]
practice_df['season'] = practice_df['month'].apply(get_season)

# Aggregate intervals to season level
season_df = practice_df[practice_df['season'].notnull()]
# Group by winter part and compute normalized stats
season_df = (
    season_df.groupby(['measure', 'season', 'year'])['rate_per_1000']
    .agg(['mean'])
)

# Get the value from the row where group == 'total'
max_year = practice_df['year'].max()
min_year = practice_df['year'].min()
max_year_issue = practice_df[practice_df['year'] == max_year]['month'].max() <= 5
min_year_issue = practice_df[practice_df['year'] == min_year]['month'].min() >= 8

# Normalize by summer baseline
practice_df['rate_per_1000_SummBas'] = practice_df.apply(normalize_by_summer,
    axis=1,
    args=(max_year, min_year, max_year_issue, min_year_issue)
)
# Aggregate to season level, this time with normalized values and raw values
seasonality_df = (
    practice_df.groupby(['measure', 'season', 'year'])
    .agg({
        'rate_per_1000_SummBas': ['mean', 'median', 'var', 'count'],
        'rate_per_1000': ['mean', 'median', 'var']
    })
    .reset_index()
).round(4)

# Group the full dataframe and test for difference
seasonality_df['T-test_SummBas_vs_Raw'] = (
    seasonality_df
    .apply(test_difference, axis=1)
)
seasonality_df.columns = ['_'.join(col).strip('_') for col in seasonality_df.columns.values]
seasonality_df.to_csv("output/practice_measures/seasonality_results.csv")

# --------------- Describing long-term trend --------------------------------------------

practice_df['weeks_from_start'] = (
        practice_df['interval_start'] - study_start_date
    ).dt.days / 7
results_dict = {}
for measure in measures:
    # Use mask instead of filter so that view is used instead of copy (saves memory)
    mask = practice_df['measure'] == measure
    # Create column for time since start
    practice_df.loc[mask, 'weeks_from_start'] = (
        practice_df.loc[mask, 'interval_start'] - study_start_date
    ).dt.days / 7
    res_SumBas = stats.linregress(practice_df.loc[mask, 'weeks_from_start'], practice_df.loc[mask, 'rate_per_1000_SummBas'])
    res_raw = stats.linregress(practice_df.loc[mask, 'weeks_from_start'], practice_df.loc[mask, 'rate_per_1000'])
    results_dict[measure] = {
        "slope_SumBas": res_SumBas.slope,
        "r_squared_SumBas": res_SumBas.rvalue**2,
        "variance_SumBas": stats.variation(practice_df.loc[mask, 'rate_per_1000_SummBas']),
        "slope_raw": res_raw.slope,
        "r_squared_raw": res_raw.rvalue**2,
        "variance_raw": stats.variation(practice_df.loc[mask, 'rate_per_1000'])
    }

results_df = pd.DataFrame.from_dict(results_dict, orient='index')
# Round results
results_df = results_df.round(4)
results_df.to_csv("output/practice_measures/normalization_results.csv")

