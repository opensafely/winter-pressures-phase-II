from datetime import datetime, timedelta
import resource
import pandas as pd
import numpy as np
from scipy import stats
import pyarrow.feather as feather
from wp_config_setup import args

# --------- Pre-processing functions ------------------------------------------------

def generate_annual_dates(end_date, n_years):
    """
    Generates a list of annual start dates from the start year to the end date.
    
    Args:
        end_date (str): The end date in 'YYYY-MM-DD' format.
        n_years (int): The number of years to generate.
    Returns:
        list: A list of annual start dates in 'YYYY-MM-DD' format.
    """
    # Convert the start and end dates to datetime objects
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    # Subtract 52 weeks until we reach April 2016
    dates = []
    current_date = end_date

    # Loop to subtract 52 weeks (1 year) in each iteration until April of the start year
    for i in range(n_years):
        print(f"Adding date: {current_date.strftime('%Y-%m-%d')}")
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
        print(f"Replacing rur_urb, prior values:, {df['rur_urb_class'].unique()}")
        # Convert string col to category for efficiency
        df['rur_urb_class'] = df['rur_urb_class'].astype('string')
        df['rur_urb_class'] = df['rur_urb_class'].astype('category')
        df['rur_urb_class'] = df['rur_urb_class'].cat.add_categories(['Urban', 'Rural', 'Unknown'])
        df['rur_urb_class'].fillna('Unknown', inplace = True)
        # Aggregate urban and rural subcategories
        df['rur_urb_class'] = df['rur_urb_class'].replace({
            '1': '1', '2': '1', '3': '1', '4': '1', # Urban = 1
            '5': '2', '6': '2', '7': '2', '8': '2' # Rural = 2
            }).fillna('Unknown')
        print(f"New datatype of rur_urb: {df['rur_urb_class'].dtype}")
        print(f"Post-replace values:, {df['rur_urb_class'].unique()}")

    if replace_ethnicity:
        print(f"Replacing ethnicity, prior valuess:, {df['ethnicity'].unique()}")
        # Identify missing values
        df['ethnicity'].replace('6', pd.NA, inplace=True)
        print(f"Prior Nan count: {df['ethnicity'].isna().sum()}")
        # Fill missing values with values from sus_ethnicity
        df['ethnicity'] = df['ethnicity'].fillna(df['ethnicity_sus'])
        # Convert string col to category for efficiency
        df['ethnicity'] = df['ethnicity'].astype('category')
        # Reformat ethnicity data
        df['ethnicity'] = df['ethnicity'].cat.add_categories(['White', 'Mixed', 'South Asian', 'Black', 'Other', 'Not stated'])
        df['ethnicity'].replace(
            {'1': 'White', '2': 'Mixed', '3': 'South Asian', '4': 'Black', '5': 'Other', 
             'A': 'White', 'B': 'White', 'C': 'White', 
             'D': 'Mixed', 'E': 'Mixed', 'F': 'Mixed', 'G': 'Mixed', 
             'H': 'South Asian', 'J': 'South Asian', 'K': 'South Asian', 'L': 'South Asian', 
             'M': 'Black', 'N': 'Black', 'P': 'Black', 
             'R': 'Other', 'S': 'Other', 
             'Z': 'Not stated'},
            inplace=True)
        # Fill missing values with 'Not stated'
        df['ethnicity'].fillna("Not stated", inplace=True)
        print(f"New datatype of ethnicity: {df['ethnicity'].dtype}")
        print(f"Post-replace Nan count: {df['ethnicity'].isna().sum()}")
        print(f"Post-replace values:, {df['ethnicity'].unique()}")
        df = df.drop('ethnicity_sus', axis=1)
        # Aggregate ethnicity categories
        df = df.groupby(df.cols.remove(['numerator', 'list_size']), as_index=False)['numerator', 'list_size'].sum()
        print(f"Post-replace df: {df.head()}")

    return df

# ----------- Summer-winter comparison functions ---------------------------------------------

def build_aggregates(rate_df):
    # Ensure grouping columns are correct
    grouped = rate_df.groupby(['measure', 'season', 'practice_pseudo_id', 'pandemic'])['rate_per_1000_midpoint6_derived']
    agg = grouped.agg(['sum', 'count']).rename(columns={'sum': 'total_rate', 'count': 'intervals'})
    return agg

def test_difference(row, agg_df):
    # Skip summer-summer comparisons
    if row['season'] == 'Jun-Jul':
        return np.nan

    key_summer = (row['measure'], 'Jun-Jul', row['practice_pseudo_id'], row['pandemic'])
    key_season = (row['measure'], row['season'], row['practice_pseudo_id'], row['pandemic'])

    # Fetch rates for each season
    summer_rate = round(agg_df.loc[key_summer, 'total_rate'])
    summer_n = agg_df.loc[key_summer, 'intervals']
    winter_rate = round(agg_df.loc[key_season, 'total_rate'])
    winter_n = agg_df.loc[key_season, 'intervals']

    # Skip comparisons with 0 intervals
    if summer_n == 0 or winter_n == 0:
        return np.nan

    result = stats.poisson_means_test(summer_rate, summer_rate, winter_rate, winter_n, alternative='two-sided')
    return round(result.pvalue, 4)

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
    
def read_write(read_or_write, path, test = args.test, file_type = args.file_type, df = None, dtype = None, **kwargs):
    """
    Function to read or write a file based on the test flag.
    Args:
        df (pd.DataFrame): DataFrame to write if read_or_write is 'write'.
        read_or_write (str): 'read' or 'write' to specify the operation.
        test (bool): If True, use test versions of datasets.
        file_type (str): Type of file to read/write ('csv' or 'arrow').
        path (str): Path to the file.
    Returns:
        pd.DataFrame: DataFrame read from the file if read_or_write is 'read'.
    """
    if test:
            path = path + '_test'
            
    if read_or_write == 'read':
        
        if file_type == 'csv':
            df = pd.read_csv(path + '.csv.gz', **kwargs)

        elif file_type == 'arrow':
            df = feather.read_feather(path + '.arrow')
            
            if dtype is not None:
                df = df.astype(dtype)
                df["interval_start"] = pd.to_datetime(df["interval_start"])
                # Drop columns that are not in the dtype dictionary
                df = df[df.columns.intersection(dtype.keys())]
                # Convert boolean columns to boolean type
                bool_cols = [col for col, typ in dtype.items() if typ == 'bool']
                for col in bool_cols:
                    df[col] = df[col] == 'T'

        return df

    elif read_or_write == 'write':

        if file_type == 'csv':
            df.to_csv(path + '.csv.gz', **kwargs)

        elif file_type == 'arrow':
            # Convert boolean columns to string type
            feather.write_feather(df, path + '.arrow')
