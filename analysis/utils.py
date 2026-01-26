from datetime import datetime, timedelta
import resource
import pandas as pd
import numpy as np
from scipy import stats
import pyarrow.feather as feather
import seaborn as sns
import matplotlib.pyplot as plt
from parse_args import config

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
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    # Subtract 52 weeks until we reach April 2016
    dates = []
    current_date = end_date

    # Loop to subtract 52 weeks (1 year) in each iteration until April of the start year
    for i in range(n_years):
        print(f"Adding date: {current_date.strftime('%Y-%m-%d')}")
        dates.append(current_date.strftime("%Y-%m-%d"))
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
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # In kilobytes
    usage = usage / 1024  # Convert to MB
    usage = round(usage, 2)  # Round to 2 decimal places
    print(f"usage at {label}: {usage} mb", flush=True)


def replace_nums(df, replace_ethnicity=True, replace_rur_urb=True):
    """
    Replaces numerical values with their corresponding string values for the following columns:
    - Rural urban classification
    - Ethnicity
    Args:
        df (pd.DataFrame): DataFrame to be processed
    Returns:
        pd.DataFrame: Processed DataFrame
    """
    # Reformat rur_urb column
    if replace_rur_urb:
        print(f"Replacing rur_urb, prior values:, {df['rur_urb_class'].unique()}")
        # Convert string col to category for efficiency
        df["rur_urb_class"] = df["rur_urb_class"].astype("string")
        df["rur_urb_class"] = df["rur_urb_class"].astype("category")
        df["rur_urb_class"] = df["rur_urb_class"].cat.add_categories(
            ["Urban", "Rural", "Unknown"]
        )
        df["rur_urb_class"].fillna("Unknown", inplace=True)
        # Aggregate urban and rural subcategories
        df["rur_urb_class"] = (
            df["rur_urb_class"]
            .replace(
                {
                    "1": "Urban",
                    "2": "Urban",
                    "3": "Urban",
                    "4": "Urban",  # Urban = 1
                    "5": "Rural",
                    "6": "Rural",
                    "7": "Rural",
                    "8": "Rural",  # Rural = 2
                }
            )
            .fillna("Unknown")
        )
        print(f"New datatype of rur_urb: {df['rur_urb_class'].dtype}")
        print(f"Post-replace values:, {df['rur_urb_class'].unique()}")

    if replace_ethnicity:
        print(f"Replacing ethnicity, prior valuess:, {df['ethnicity'].unique()}")
        # Identify missing values
        df["ethnicity"].replace("6", pd.NA, inplace=True)
        print(f"Prior Nan count: {df['ethnicity'].isna().sum()}")
        # Fill missing values with values from sus_ethnicity
        df["ethnicity"] = df["ethnicity"].fillna(df["ethnicity_sus"])
        # Convert string col to category for efficiency
        df["ethnicity"] = df["ethnicity"].astype("category")
        # Reformat ethnicity data
        df["ethnicity"] = df["ethnicity"].cat.add_categories(
            ["White", "Mixed", "South Asian", "Black", "Other", "Not stated"]
        )
        df["ethnicity"].replace(
            {
                "1": "White",
                "2": "Mixed",
                "3": "South Asian",
                "4": "Black",
                "5": "Other",
                "A": "White",
                "B": "White",
                "C": "White",
                "D": "Mixed",
                "E": "Mixed",
                "F": "Mixed",
                "G": "Mixed",
                "H": "South Asian",
                "J": "South Asian",
                "K": "South Asian",
                "L": "South Asian",
                "M": "Black",
                "N": "Black",
                "P": "Black",
                "R": "Other",
                "S": "Other",
                "Z": "Not stated",
            },
            inplace=True,
        )
        # Fill missing values with 'Not stated'
        df["ethnicity"].fillna("Not stated", inplace=True)
        print(f"New datatype of ethnicity: {df['ethnicity'].dtype}")
        print(f"Post-replace Nan count: {df['ethnicity'].isna().sum()}")
        print(f"Post-replace values:, {df['ethnicity'].unique()}")
        df = df.drop("ethnicity_sus", axis=1)
        # Aggregate ethnicity categories
        group_cols = [
            col for col in df.columns if col not in ["numerator", "list_size"]
        ]
        df = df.groupby(group_cols, as_index=False, observed=True)[
            ["numerator", "list_size"]
        ].sum()
        print(f"Post-replace df: {df.head()}")

    return df


# ----------- Summer-winter comparison functions ---------------------------------------------


def build_aggregate_df(rate_df, strata, aggregation_dict):
    # Ensure grouping columns are correct
    agg = (rate_df.groupby(strata).agg(aggregation_dict)).reset_index()
    agg.columns = ["_".join(col).strip("_") for col in agg.columns.values]
    return agg


def transpose_summer(df, baseline):

    # 1. Extract the baseline (Jun-Jul rows) CURRENTLY PREV SUMMER ONLY
    summer_df = df[df["season"] == "Jun-Jul"][
        ["measure", "pandemic", "rate_per_1000_midpoint6_derived"]
    ]
    summer_df = summer_df.rename(
        columns={"rate_per_1000_midpoint6_derived": f"{baseline}_rate"}
    )

    # 2. Merge baseline back on measure + pandemic
    df = df.merge(summer_df, on=["measure", "pandemic"], how="left")

    # 3. Compute rate ratio
    df["RR"] = df["rate_per_1000_midpoint6_derived"] / df[f"{baseline}_rate"]

    return df


def test_difference(row, agg_df):

    # Skip summer-summer comparisons
    if row["season"] == "Jun-Jul":
        return np.nan

    key_summer = (row["measure"], "Jun-Jul", row["practice_pseudo_id"], row["pandemic"])
    key_season = (
        row["measure"],
        row["season"],
        row["practice_pseudo_id"],
        row["pandemic"],
    )

    print(f"Comparing {key_season} with {key_summer}")

    # Fetch rates for each season NEED TO UPDATE TOTAL_RATE
    summer_rate = round(agg_df.loc[key_summer, "total_rate"])
    summer_n = agg_df.loc[key_summer, "intervals"]
    winter_rate = round(agg_df.loc[key_season, "total_rate"])
    winter_n = agg_df.loc[key_season, "intervals"]

    # Skip comparisons with 0 intervals
    if summer_n == 0 or winter_n == 0:
        print("Skipping as n = 0")
        return np.nan

    result = stats.poisson_means_test(
        summer_rate, summer_n, winter_rate, winter_n, alternative="two-sided"
    )
    return round(result.pvalue, 4)


def get_season(month):
    """
    Returns the season for a given month.
    Args:
        month (int): Month number (1-12).
    Returns:
        str: Season name (2 month period).
    """
    if month in [9, 10]:
        return "Sep-Oct"
    elif month in [11, 12]:
        return "Nov-Dec"
    elif month in [1, 2]:
        return "Jan-Feb"
    elif month in [6, 7]:
        return "Jun-Jul"
    else:
        return None  # Exclude non-winter months


def read_write(
    read_or_write,
    path,
    file_type="arrow",
    test=config["test"],
    yearly=config["yearly"],
    df=None,
    dtype=None,
    **kwargs,
):
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
    if yearly:
        path = path + "_yearly"
        
    if test:
        path = path + "_test"

    if read_or_write == "read":

        if file_type == "csv":
            df = pd.read_csv(path + ".csv", **kwargs)

        elif file_type == "arrow":
            df = feather.read_feather(path + ".arrow")

            if dtype is not None:
                df = df.astype(dtype)
                df["interval_start"] = pd.to_datetime(df["interval_start"])

                # Convert boolean columns to boolean type
                bool_cols = [col for col, typ in dtype.items() if typ == "bool"]
                for col in bool_cols:
                    df[col] = df[col] == "T"

            return df

    elif read_or_write == "write":

        if df is None:
            raise Exception("Must supply dataframe when writing")

        if file_type == "csv":
            df.to_csv(path + ".csv", **kwargs)

        elif file_type == "arrow":
            # Convert boolean columns to string type
            feather.write_feather(df, path + ".arrow")


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
        if dtype == "int64":
            data[col] = np.random.randint(0, 1000, size=n_rows)
        elif dtype == "int16":
            data[col] = np.random.randint(-30000, 30000, size=n_rows).astype(np.int16)
        elif dtype == "int8":
            data[col] = np.random.randint(1, 6, size=n_rows).astype(np.int8)
        elif dtype == "bool":
            data[col] = np.random.choice(["T", "F"], size=n_rows)
        elif dtype == "category":
            data[col] = pd.Categorical(np.random.choice(["A", "B", "C"], size=n_rows))
        elif dtype == "string":
            data[col] = pd.Series(
                np.random.choice(["x", "y", "z", None], size=n_rows), dtype="string"
            )
        else:
            raise ValueError(f"Unhandled dtype: {dtype}")

    df = pd.DataFrame(data).astype(dtype_dict)
    return df


def merge_seasons(summer_df, non_summer_df, practice_level):
    """
    Merges summer (baseline) and non-summer dataframes
    Args:
        summer_df: Summer dataframe of counts
        non_summer_df: Non-Summer dataframe of counts
        practice_level: Boolean, determines whether merging is done at practice level
    Returns:
        pd.DataFrame: Merged dataframe containing columns for summer and non_summer rates per measure
    """

    # Merge keys: use summer_year, measure, pandemic, and practice if practice_level
    merge_cols = ["measure", "summer_year", "pandemic"]
    if practice_level:
        merge_cols.append("practice_pseudo_id")

    # Perform left merge: every non-summer row gets the same summer baseline
    combined_seasons_df = non_summer_df.merge(
        summer_df, on=merge_cols, how="left", suffixes=[None, "_prev_summr"]
    )

    # Find the first valid summer year for each measure
    first_summer_years = summer_df.groupby("measure")["summer_year"].min().reset_index()
    # Merge to keep only the first summer for a given practice and measure
    first_summer_df = summer_df.merge(
        first_summer_years, on=["measure", "summer_year"]
    ).drop(
        columns="summer_year"
    )  # Drop original summer_year after filtering

    # Merge first summer counts into main df
    merge_cols = ["measure", "pandemic"]
    if practice_level == True:
        merge_cols.append("practice_pseudo_id")

    combined_seasons_df_final = combined_seasons_df.merge(
        first_summer_df, on=merge_cols, how="left", suffixes=[None, "_first_summr"]
    )

    return combined_seasons_df_final

def generate_dist_plot(df, var, facet_var, **kwargs):
    
    facet_plot = sns.FacetGrid(
        data = df,
        col=facet_var,
        col_wrap=4,
        height=4,
        aspect=1,
        sharex=False,   # ✅ works properly here
        sharey=False
    )

    facet_plot.map_dataframe(sns.histplot, x = var, element="bars")

    return facet_plot
