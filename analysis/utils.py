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
            '1': 'Urban', '2': 'Urban', '3': 'Urban', '4': 'Urban', # Urban = 1
            '5': 'Rural', '6': 'Rural', '7': 'Rural', '8': 'Rural' # Rural = 2
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
        group_cols = [col for col in df.columns if col not in ['numerator', 'list_size']]
        df = df.groupby(group_cols, as_index=False, observed = True)[['numerator', 'list_size']].sum()
        print(f"Post-replace df: {df.head()}")

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
    
def read_write(read_or_write, path, test = args.test, df = None, dtype = None, **kwargs):
    """
    Function to read or write a file based on the test flag.
    Args:
        df (pd.DataFrame): DataFrame to write if read_or_write is 'write'.
        read_or_write (str): 'read' or 'write' to specify the operation.
        test (bool): If True, use test versions of datasets.
        path (str): Path to the file.
    Returns:
        pd.DataFrame: DataFrame read from the file if read_or_write is 'read'.
    """
    if test:
            path = path + '_test'
            
    if read_or_write == 'read':
            
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

        # Convert boolean columns to string type
        feather.write_feather(df, path + '.arrow')

def simulate_dataframe(dtype_dict, n_rows):
    """
    Simulate a DataFrame with specified dtypes and number of rows.
    Args:
        dtype_dict (dict): Dictionary mapping column names to dtypes.
        n_rows (int): Number of rows to generate.
    Returns:
        pd.DataFrame: Simulated DataFrame with specified dtypes.
    """
    data = {}
    for col, dtype in dtype_dict.items():
        if dtype == 'int64':
            data[col] = np.random.randint(0, 1000, size=n_rows)
        elif dtype == 'int16':
            data[col] = np.random.randint(-30000, 30000, size=n_rows).astype(np.int16)
        elif dtype == 'int8':
            data[col] = np.random.randint(1, 6, size=n_rows).astype(np.int8)
        elif dtype == 'bool':
            data[col] = np.random.choice(['T', 'F'], size=n_rows)
        elif dtype == 'category':
            data[col] = pd.Categorical(np.random.choice(['A', 'B', 'C'], size=n_rows))
        elif dtype == 'string':
            data[col] = pd.Series(np.random.choice(['x', 'y', 'z', None], size=n_rows), dtype='string')
        else:
            raise ValueError(f"Unhandled dtype: {dtype}")

    df = pd.DataFrame(data).astype(dtype_dict)
    return df
