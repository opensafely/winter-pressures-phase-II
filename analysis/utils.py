from datetime import datetime, timedelta
import resource
import pandas as pd
import numpy as np
from scipy import stats
import pyarrow.feather as feather
import seaborn as sns
import matplotlib.pyplot as plt
from parse_args import config
import pickle

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


def replace_nums(df, replace_ethnicity=True, replace_rur_urb=True, **kwargs):
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

        # 'Demograph measures' will require not filtering on measures with 'ethnicity' in the name
        if config["practice_subgroup_measures"] == True:

            print(f"Replacing ethnicity, prior valuess:, {df['ethnicity'].unique()}")
            df_ethnicity = df[
                df["measure"].str.contains("ethnicity", case=False, na=False)
            ]
            # Identify missing values
            df_ethnicity["ethnicity"].replace("6", pd.NA, inplace=True)
            print(f"Prior Nan count: {df_ethnicity['ethnicity'].isna().sum()}")
            # Fill missing values with values from sus_ethnicity
            df_ethnicity["ethnicity"] = df_ethnicity["ethnicity"].fillna(
                df_ethnicity["ethnicity_sus"]
            )
            # Convert string col to category for efficiency
            df_ethnicity["ethnicity"] = df_ethnicity["ethnicity"].astype("category")
            # Reformat ethnicity data
            df_ethnicity["ethnicity"] = df_ethnicity["ethnicity"].cat.add_categories(
                ["White", "Mixed", "South Asian", "Black", "Other", "Not stated"]
            )
            df_ethnicity["ethnicity"].replace(
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
            # Impute missing ethnicity with ethnicity sus
            df_ethnicity["ethnicity"] = df_ethnicity["ethnicity"].fillna(
                df_ethnicity["ethnicity_sus"]
            )
            print(f"New datatype of ethnicity: {df_ethnicity['ethnicity'].dtype}")
            print(f"Post-replace Nan count: {df_ethnicity['ethnicity'].isna().sum()}")
            print(
                f"Post-replace ehtnicity values:, {df_ethnicity['ethnicity'].unique()}"
            )
            df = df.drop("ethnicity_sus", axis=1)
            df_ethnicity = df_ethnicity.drop("ethnicity_sus", axis=1)

            # Aggregate ethnicity categories
            group_cols = [
                col
                for col in df_ethnicity.columns
                if col not in ["numerator", "list_size"]
            ]
            df_ethnicity = df_ethnicity.groupby(
                group_cols, as_index=False, observed=True, dropna=False
            )[["numerator", "list_size"]].sum()

            # Drop original ethnicity measures and merge back aggregated measures
            df = df[~df["measure"].str.contains("ethnicity", case=False, na=False)]
            df = pd.concat([df, df_ethnicity], ignore_index=True)

            print(f"Post-aggregation values:, {df['ethnicity'].unique()}")
            print(f"Post-replace df: {df.head()}")

    return df


# ----------- Summer-winter comparison functions ---------------------------------------------


def flatten_multiindex_columns(df):
    """
    Flattens multi-index columns in a DataFrame by joining the levels with an underscore.
    Args:
        df (pd.DataFrame): DataFrame with multi-index columns.
    Returns:
        pd.DataFrame: DataFrame with flattened column names.
    """
    # Handle both MultiIndex (tuple) and single-level column indexes safely
    new_columns = []
    for col in df.columns.values:
        if isinstance(col, tuple):
            # Join non-None parts of the tuple with underscores
            parts = [str(part) for part in col if part is not None]
            new_col = "_".join(parts).strip("_")
        else:
            # Single-level column: use its string representation directly
            new_col = str(col)
        new_columns.append(new_col)

    df = df.copy()
    df.columns = new_columns
    return df


def build_aggregate_df(rate_df, strata, aggregation_dict, initial_list_size=False):
    """
    Builds an aggregate DataFrame based on the specified grouping columns and aggregation functions.
    Args:
    - rate_df (pd.DataFrame): The input DataFrame containing the data to be aggregated
    - strata (list): List of column names to group by
    - aggregation_dict (dict): Dictionary specifying the aggregation functions for each column
    - initial_list_size (bool): If True, calculates the list size at the first interval
    """

    # Ensure grouping columns are correct
    agg = (rate_df.groupby(strata, observed=True).agg(aggregation_dict)).reset_index()
    agg = flatten_multiindex_columns(agg)

    # If initial list size desired, use the first national-week list_size as
    # yearly list size to avoid inflating list_size by summing list sizes
    # across weeks or accidentally taking a practice-level list_size value.
    if initial_list_size == True:
        if (
            "list_size" not in rate_df.columns
            or "interval_start" not in rate_df.columns
        ):
            raise ValueError(
                "initial_list_size=True requires 'list_size' and 'interval_start' columns in rate_df"
            )

        # Aggregate list_size to national-week level first (sum across rows),
        # then take the earliest week list_size within each stratum.
        strata_no_interval = [col for col in strata if col != "interval_start"]
        weekly_strata = list(dict.fromkeys(strata_no_interval + ["interval_start"]))

        weekly_list_size = rate_df.groupby(
            weekly_strata, as_index=False, observed=True
        )["list_size"].sum()

        first_week_list_size = (
            weekly_list_size.sort_values("interval_start")
            .groupby(strata_no_interval, as_index=False, observed=True)["list_size"]
            .first()
        )

        first_week_list_size = flatten_multiindex_columns(first_week_list_size)
        agg = agg.merge(first_week_list_size, on=strata_no_interval, how="left")

        # Rename list_size column to reflect that it's the first week list_size, not the sum of weekly list_sizes
        agg.rename(columns={"list_size": "list_size_initial"}, inplace=True)

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
    elif month in [3]:
        return "Mar"  # QOF deadline to flag for qof inflation, important for sro
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
        df (pd.DataFrame/Dict): DataFrame/Dict to write if read_or_write is 'write'.
        read_or_write (str): 'read' or 'write' to specify the operation.
        test (bool): If True, use test versions of datasets.
        path (str): Path to the file.
    Returns:
        pd.DataFrame: DataFrame read from the file if read_or_write is 'read'.
    """

    if test:
        path = path + "_test"

    if read_or_write == "read":

        if file_type == "csv":
            df = pd.read_csv(path + ".csv", **kwargs)

        elif file_type == "csv.gz":
            df = pd.read_csv(path + ".csv.gz", compression="gzip", **kwargs)

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

        elif file_type == "pickle":
            with open(path + ".pickle", "rb") as handle:
                df = pickle.load(handle)
            return df

    elif read_or_write == "write":

        if df is None:
            raise Exception("Must supply dataframe when writing")

        if file_type == "csv":
            df.to_csv(path + ".csv", **kwargs)

        elif file_type == "csv.gz":
            df.to_csv(path + ".csv.gz", compression="gzip", **kwargs)

        elif file_type == "arrow":
            # Convert boolean columns to string type
            feather.write_feather(df, path + ".arrow")

        elif file_type == "pickle":
            with open(path + ".pickle", "wb") as handle:
                pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)


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

    # Merge first-summer baseline independent of pandemic period so
    # post-pandemic rows can still reference the 2016 summer baseline.
    merge_cols = ["measure"]
    if practice_level == True:
        merge_cols.append("practice_pseudo_id")

    combined_seasons_df_final = combined_seasons_df.merge(
        first_summer_df, on=merge_cols, how="left", suffixes=[None, "_first_summr"]
    )

    return combined_seasons_df_final


def generate_dist_plot(df, var, facet_var, **kwargs):

    facet_plot = sns.FacetGrid(
        data=df,
        col=facet_var,
        col_wrap=4,
        height=4,
        aspect=1,
        sharex=False,  # ✅ works properly here
        sharey=False,
    )

    facet_plot.map_dataframe(sns.histplot, x=var, element="bars")

    return facet_plot


def _print_rounding_checks(unrounded, rounded, col_name, low_value_threshold=10):
    """
    Print rounding checks comparing rounded vs unrounded values for a column.
    """
    unrounded_series = pd.Series(unrounded).astype("float64")
    rounded_series = pd.Series(rounded).astype("float64")

    rounding_difference = rounded_series - unrounded_series
    rounding_diff_counts = rounding_difference.value_counts(dropna=False).sort_index()
    print(
        f"Rounding difference counts for {col_name}:\n{rounding_diff_counts}",
        flush=True,
    )

    low_unrounded = (
        unrounded_series[unrounded_series < low_value_threshold]
        .value_counts(dropna=False)
        .sort_index()
    )
    low_rounded = (
        rounded_series[rounded_series < low_value_threshold]
        .value_counts(dropna=False)
        .sort_index()
    )
    print(
        f"Low unrounded value counts for {col_name} (< {low_value_threshold}):\n{low_unrounded}",
        flush=True,
    )
    print(
        f"Low rounded value counts for {col_name} (< {low_value_threshold}):\n{low_rounded}",
        flush=True,
    )


def roundmid_any(x, to=6, low_value_threshold=10):
    """
    Round values using midpoint rounding and always print checks comparing
    rounded and unrounded counts.
    Args:
    - x: DataFrame of values to be rounded
    - to: The number to which to round (e.g., 6 for rounding to the nearest 6)
    - low_value_threshold: Threshold below which to print value counts for rounded and unrounded values 
                            to check for potential over-rounding of low values.
    """

    rounded = np.ceil(x / to) * to - (np.floor(to / 2) * (x != 0))

    # Print changes caused by rounding
    for col in x.columns:
        _print_rounding_checks(
            x[col],
            rounded[col],
            col_name=col,
            low_value_threshold=low_value_threshold,
        )

    return rounded

def column_total_check(df, column, year, measure_name):

    total_count = df[
        (df["measure"] == measure_name) & (df["interval_start"].dt.year == year)
    ][column].sum()

    return f"Total {measure_name} cases in {year}: {total_count}"


def aggregate_unweighted_rr_results(practice_level_df, group_cols):
    """
    Aggregate RR medians, RD medians, and proportions of RR direction.
    Args:
    - practice_level_df: DataFrame with practice-level RRs and rate differences.
    - group_cols: List of columns to group by for aggregation (e.g., measure, season, pandemic).
    """

    df = practice_level_df.copy()

    # Indicator columns for RR direction used in grouped counts.
    for baseline in ["prev_summr", "first_summr"]:
        rr_col = f"RR_{baseline}"
        df[f"{rr_col}_>5%"] = df[rr_col] > 1.05
        df[f"{rr_col}_=1"] = (df[rr_col] >= 0.95) & (df[rr_col] <= 1.05)
        df[f"{rr_col}_<5%"] = df[rr_col] < 0.95

    results_df = build_aggregate_df(
        df,
        group_cols,
        {
            "RR_prev_summr": ["median"],
            "RR_first_summr": ["median"],
            "list_size_count_first_summr": ["sum"],
            "list_size_count_prev_summr": ["sum"],
            "RD_prev_summr": ["median"],
            "RD_first_summr": ["median"],
            "RR_prev_summr_>5%": ["sum"],
            "RR_prev_summr_=1": ["sum"],
            "RR_prev_summr_<5%": ["sum"],
            "RR_first_summr_>5%": ["sum"],
            "RR_first_summr_=1": ["sum"],
            "RR_first_summr_<5%": ["sum"],
        },
    )

    # Proportion of practices with RR > 1, = 1, and < 1.
    results_df["%_RR_prev_>5%"] = (
        results_df["RR_prev_summr_>5%_sum"]
        / results_df["list_size_count_prev_summr_sum"]
    )
    results_df["%_RR_prev_=1"] = (
        results_df["RR_prev_summr_=1_sum"]
        / results_df["list_size_count_prev_summr_sum"]
    )
    results_df["%_RR_prev_<5%"] = (
        results_df["RR_prev_summr_<5%_sum"]
        / results_df["list_size_count_prev_summr_sum"]
    )
    results_df["%_RR_first_>5%"] = (
        results_df["RR_first_summr_>5%_sum"]
        / results_df["list_size_count_first_summr_sum"]
    )
    results_df["%_RR_first_=1"] = (
        results_df["RR_first_summr_=1_sum"]
        / results_df["list_size_count_first_summr_sum"]
    )
    results_df["%_RR_first_<5%"] = (
        results_df["RR_first_summr_<5%_sum"]
        / results_df["list_size_count_first_summr_sum"]
    )

    results_df = results_df.drop(
        columns=[
            "RR_prev_summr_>5%_sum",
            "RR_prev_summr_=1_sum",
            "RR_prev_summr_<5%_sum",
            "RR_first_summr_>5%_sum",
            "RR_first_summr_=1_sum",
            "RR_first_summr_<5%_sum",
        ]
    )

    return results_df


def filter_pandemic_mismatches(df):
    # Filter out pandemic period mismatches

    if config["test"]:
        pandemic_start_year = pd.to_datetime(
            config["test_config"]["pandemic_start"]
        ).year
        pandemic_end_year = pd.to_datetime(config["test_config"]["pandemic_end"]).year
    else:
        pandemic_start_year = pd.to_datetime(config["pandemic_start"]).year
        pandemic_end_year = pd.to_datetime(config["pandemic_end"]).year

    summer_year = pd.to_numeric(df["summer_year"], errors="coerce")

    return df[
        ~(
            ((df["pandemic"] == "Before") & (summer_year > pandemic_end_year))
            | ((df["pandemic"] == "After") & (summer_year < pandemic_start_year))
        )
    ]


def calculate_rate_ratios(summer_df, non_summer_df, practice_level):
    """
    Calculates rate ratios and rate differences comparing each season to the two summer baselines (prev summer and first summer).
    """

    rr_df = merge_seasons(summer_df, non_summer_df, practice_level=practice_level)

    # National level has additional level of aggregation, so use the higher aggregate column counts when practice level = False
    if practice_level == True:
        numerator_col = "numerator_sum"
        denominator_col = "list_size_initial"
    else:
        numerator_col = "numerator_sum_sum"
        denominator_col = "list_size_initial_sum"

    # Calculate rate ratios
    rr_df["Rate_per_1000"] = (rr_df[numerator_col] / rr_df[denominator_col]) * 1000
    baselines = ["_prev_summr", "_first_summr"]

    for baseline in baselines:
        rr_df[f"{'Rate_per_1000'}{baseline}"] = (
            rr_df[f"{numerator_col}{baseline}"] / rr_df[f"{denominator_col}{baseline}"]
        ) * 1000
        rr_df[f"RR{baseline}"] = (
            rr_df["Rate_per_1000"] / rr_df[f"{'Rate_per_1000'}{baseline}"]
        )
        rr_df[f"RD{baseline}"] = (
            rr_df["Rate_per_1000"] - rr_df[f"{'Rate_per_1000'}{baseline}"]
        )

    filtered_rr_df = filter_pandemic_mismatches(rr_df)
    return filtered_rr_df
