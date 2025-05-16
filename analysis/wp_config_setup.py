# This script sets up the configuration for the analysis pipeline.
# It includes the command-line argument options to customize the behaviour of each action.

import argparse
parser = argparse.ArgumentParser() # Instantiate parser

# Configuration for add measures
parser.add_argument("--add_indicat_prescript", action = 'store_true', help = "Adds indicat/prescript if flag is added to action.")
parser.add_argument("--add_prescriptions", action = 'store_true', help = "Adds prescriptions if flag is added to action.") 
parser.add_argument("--add_reason", action = 'store_true', help = "Adds reason if flag is added to action.") 
parser.add_argument("--demograph_measures", action= 'store_true', help = "Sets measures defaults to demographic-level subgroups")
parser.add_argument("--practice_measures", action= 'store_true', help = "Sets measures defaults to practice-level subrgoups")
parser.add_argument("--comorbid_measures", action= 'store_true', help = "Sets measures defaults to comorbidity-level subgroups")

# Configuration for interval date input
parser.add_argument("--start_intv", help="Interval start date")
parser.add_argument("--test", action= 'store_true', help = "Sets lowest time intervals for lightweight testing")

args = parser.parse_args() # Stores arguments in 'args'

# Configure dates
args.study_start_date = "2025-03-31"
args.n_years = 10