# This script sets up the configuration for the Python analysis pipeline.
# It reads in user command-line arguments and then extracts the appropriate
# configuration settings from config.json based on those arguments.

import argparse
import json

# Load default config from JSON
with open("analysis/config.json", "r") as f:
    config = json.load(f)

parser = argparse.ArgumentParser()  # Instantiate parser

# ----------------- Parse user arguments -------------------------------

# Configuration for add measures
parser.add_argument(
    "--add_indicat_prescript",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Adds indicat/prescript if flag is added to action.",
)
parser.add_argument(
    "--add_prescriptions",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Adds prescriptions if flag is added to action.",
)
parser.add_argument(
    "--add_reason",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Adds reason if flag is added to action.",
)
parser.add_argument(
    "--demograph_measures",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Sets measures defaults to demographic-level subgroups",
)
parser.add_argument(
    "--practice_measures",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Sets measures defaults to practice-level subgroups",
)
parser.add_argument(
    "--comorbid_measures",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Sets measures defaults to comorbidity-level subgroups",
)
parser.add_argument(
    "--practice_subgroup_measures",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Sets measures defaults to practice subgroup-level subgroups",
)
parser.add_argument(
    "--use_csv",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Uses csv instead of arrow for ease of file inspection",
)
parser.add_argument(
    "--set",
    default=argparse.SUPPRESS,
    help="Choose which set of measures to extract: appts_table, sro, resp",
)

# Configuration for interval date input
parser.add_argument(
    "--start_intv", default=argparse.SUPPRESS, help="Interval start date"
)
parser.add_argument(
    "--yearly",
    action = "store_true",
    default=argparse.SUPPRESS,
    help="Set intervals to yearly instead of weekly",
)
parser.add_argument(
    "--weekly_agg",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Set yearly intervals to be aggregated from weekly measures",
)
parser.add_argument(
    "--test",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Sets lowest time intervals for lightweight testing",
)

# Restrict measure to those with an appt
parser.add_argument(
    "--appt",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Restrict measures to those with an appointment in interval",
)

args = parser.parse_args()  # Stores arguments in 'args'

# Override config with provided args
for key, value in vars(args).items():
    config[key] = value

# ----------------- Apply conditional logic to config -------------------

# Initialize dtype_dict with base
config["dtype_dict"] = config["base_dtype_dict"].copy()

# Apply group-specific configuration
for group in ["demograph", "practice", "comorbid", "practice_subgroup"]:
    if config.get(f"{group}_measures", False):
        # Set group in config and update dtype_dict
        config["group"] = group
        config["dtype_dict"].update(config["groups"][group]["dtype_dict"])
        break  # Only one group can be selected

if config.get("appt", False):
    config["appt_suffix"] = "_appt"

if config.get("weekly_agg", False):
    config["agg_suffix"] = "_weeklyagg"

if config.get("test", False):
    config["test_suffix"] = "_test"

config["deprioritized"] = set(config["sro_dict"].keys()) - set(config["prioritized"])

if config.get("use_csv", False):
    config["file_type"] = "csv"

if config.get("set") == "sro":
    config["pipeline_measures"] = config["measures_list"]["sro"]
elif config.get("set") == "resp":
    config["pipeline_measures"] = config["measures_list"]["resp"]
elif config.get("set") == "appts_table":
    config["pipeline_measures"] = config["measures_list"]["appts_table"]