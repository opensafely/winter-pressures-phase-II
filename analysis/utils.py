#TODO:
# Uncomment datatype conversion if memory still fails
from datetime import datetime, timedelta
import resource
import pandas as pd

def generate_annual_dates(start_year, end_date):
    """
    Generates a list of annual start dates from the start year to the end date.
    
    Args:
        start_year: The starting year for the dates.
        end_date: The end date for the dates.
        
    Returns:
        A list of start dates (52 weeks apart from each other) in 'YYYY-MM-DD' format.
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
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"usage at {label}: {usage} kb", flush=True)  # In kilobytes on Linux, bytes on macOS

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