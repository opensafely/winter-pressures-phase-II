# This script sets up the configuration for the Python analysis pipeline.
# It reads in user command-line arguments and then extracts the appropriate
# configuration settings from config.json based on those arguments.

import argparse
import json

# Load default config from JSON
with open("config.json", "r") as f:
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
    "--use_csv",
    action="store_true",
    default=argparse.SUPPRESS,
    help="Uses csv instead of arrow for ease of file inspection",
)
parser.add_argument(
    "--set",
    default=argparse.SUPPRESS,
    help="Choose which set of measures to extract: all, sro, resp",
)

# Configuration for interval date input
parser.add_argument(
    "--start_intv", default=argparse.SUPPRESS, help="Interval start date"
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

# Set defaults from config
for key, value in config.items():
    if not hasattr(args, key):
        setattr(args, key, value)

# ----------------- Configuration of constants for pipeline -------------------

# Configure dates
if args.test:
    args.pandemic_start = "2017-03-01"
    args.pandemic_end = "2018-05-17"

# Initialize dtype_dict with base
args.dtype_dict = config["base_dtype_dict"].copy()

# Apply group-specific configuration
if args.demograph_measures:
    group_config = config["groups"]["demograph"]
    args.group = group_config["group"]
    args.dtype_dict.update(group_config["dtype_dict"])
elif args.practice_measures:
    group_config = config["groups"]["practice"]
    args.group = group_config["group"]
    args.dtype_dict.update(group_config["dtype_dict"])
elif args.comorbid_measures:
    group_config = config["groups"]["comorbid"]
    args.group = group_config["group"]
    args.dtype_dict.update(group_config["dtype_dict"])

if args.appt:
    args.appt_suffix = "_appt"

args.deprioritized = set(args.sro_dict.keys()) - set(args.prioritized)

if args.use_csv:
    args.file_type = "csv"
