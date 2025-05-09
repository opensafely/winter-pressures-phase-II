from datetime import datetime, timedelta
import resource
import pandas as pd
import numpy as np
from scipy import stats

# --------- Pre-processing functions ------------------------------------------------

def generate_annual_dates(start_year, end_date):
    """
    Generates a list of annual start dates from the start year to the end date.
    
    Args:
        start_year: The starting year for the dates.
        end_date: The end date for the dates.
        
    Returns:
        A list of strings representing the annual start dates in 'YYYY-MM-DD' format.
    """
    # Generate annual start days for the study period: August 2016 -  31 July 2024
    start_date = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(weeks=52)

    # Subtract 52 weeks until we reach August 2016
    dates = []
    current_date = start_date

    # Loop to subtract 52 weeks (1 year) in each iteration
    while current_date.year > start_year or (current_date.year == start_year and current_date.month > 7):
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date -= timedelta(weeks=52)

    dates.reverse()
    return dates

def log_memory_usage(label=""):
    """
    Logs the memory usage of the current process.
    Args:
        label (str): A label to identify the point at which the memory usage is logged.
    Returns:
        Prints the memory usage in kilobytes to the action log.
    """
    usage = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) # In kilobytes
    usage = usage / 1024  # Convert to MB
    usage = round(usage, 2)  # Round to 2 decimal places
    print(f"usage at {label}: {usage} mb", flush=True)  

def replace_nums(df, replace_ethnicity=True, replace_rur_urb=True):
    '''
    Replaces numerical values with their corresponding string values for the following columns:
    - Rural urban classification
    - Ethnicity
    Args:
        df (pd.DataFrame): DataFrame to be processed
    Returns:
        pd.DataFrame: Processed DataFrame
    '''
    # Reformat rur_urb column
    if replace_rur_urb:
        print('Replacing rur_urb')
        df['rur_urb_class'].replace(
            {1: 'Urban major conurbation', 2: 'Urban minor conurbation', 3: 'Urban city and town', 
            4: 'Urban city and town in a sparse setting', 5: 'Rural town and fringe',
            6: 'Rural town and fringe in a sparse setting', 7: 'Rural village and dispersed',
            8: 'Rural village and dispersed in a sparse setting'},
            inplace=True)
        df['rur_urb_class'].fillna("Unknown", inplace = True)
        #df['rur_urb_class'] = df['rur_urb_class'].astype('category')

    if replace_ethnicity:
        print('Replacing ethnicity')
        # Reformat ethnicity data
        df['ethnicity'].replace(
            {1: 'White', 2: 'Mixed', 3: 'South Asian', 4: 'Black', 5: 'Other'},
            inplace=True)
        df['ethnicity'].fillna('Not Stated', inplace=True)
        #df['ethnicity'] = df['ethnicity'].astype('category')

    return df

# ----------- Summer-winter comparison functions ---------------------------------------------

def compare_to_summer(row, max_year, min_year, max_year_issue, min_year_issue, diff, season_df):
    '''
    Calculates the difference between the rate and the summer baseline for a given measure and year.
    Args:
        row (pd.Series): Row of the DataFrame containing the measure, year, and rate.
        max_year (int): Maximum year in the dataset.
        min_year (int): Minimum year in the dataset.
        max_year_issue (bool): Whether the latest year has no summer. Prev year summer used instead.
        min_year_issue (bool): Whether the earliest year has no summer. Next year summer used instead.
        diff (str): Type of difference to calculate ('Abs', 'Rel', 'Both').
        season_df (pd.DataFrame): DataFrame containing the summer values for each measure and year.
    Returns:
        float: The difference between the rate and the summer baseline.
    '''
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
    if diff == 'Abs':
        # Calculate absolute difference
        return row.rate_per_1000_midpoint6_derived - summer_value
    elif diff == 'Rel':
        # Calculate relative difference
        return row.rate_per_1000_midpoint6_derived / summer_value
    elif diff == 'Both':
        # Calculate both absolute and relative difference
        return pd.Series({'rate_diff': row.rate_per_1000_midpoint6_derived - summer_value, 'RR': row.rate_per_1000_midpoint6_derived / summer_value})

def test_difference(row, rate_df):
    '''
    Conducts a poisson means test comparing the summer and winter rates for a given measure, season and practice.
    Args:
        row (pd.Series): Row of the DataFrame containing the measure, season, and practice.
        rate_df (pd.DataFrame): DataFrame containing the rate data. Should be interval-level.
    Returns:
        float: The p-value of the difference between summer and winter values.
    '''
    print(f"Testing difference for measure: {row['measure']}, season: {row['season']}, practice: {row['practice_pseudo_id']}")
    if row['season'] == 'Jun-Jul':
        print("Skipping summer-summer comparison")
        return np.nan
    # Extract the summer and winter values for the measure, season, and year
    summer = rate_df.loc[
        (rate_df['measure'] == row['measure']) &
        (rate_df['season'] == 'Jun-Jul') &
        (rate_df['practice_pseudo_id'] == row['practice_pseudo_id'])
        ]
    season = rate_df.loc[
        (rate_df['measure'] == row['measure']) &
        (rate_df['season'] == row['season']) &
        (rate_df['practice_pseudo_id'] == row['practice_pseudo_id'])
        ]
    # Get the rates for summer and winter
    vals_summer = summer['rate_per_1000_midpoint6_derived']
    vals_season = season['rate_per_1000_midpoint6_derived']
    
    # Conduct poisson test
    rate1 = round(vals_summer.sum())
    intervals1 = len(vals_summer)
    print(f"Rate summer: {rate1}, Intervals summer: {intervals1}")
    rate2 = round(vals_season.sum())
    intervals2 = len(vals_season)
    print(f"Rate season: {rate2}, Intervals season: {intervals2}")
    if intervals1 == 0 or intervals2 == 0:
        print("One of the counts is zero, returning NaN")
        return np.nan
    result = stats.poisson_means_test(rate1, intervals1, rate2, intervals2, alternative='two-sided')

    # Get the p-value
    pval = result.pvalue

    # Return significance at p < 0.05
    return round(pval, 4)

def get_season(month):
    '''
    Returns the season for a given month.
    Args:
        month (int): Month number (1-12).
    Returns:
        str: Season name (2 month period).
    '''
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