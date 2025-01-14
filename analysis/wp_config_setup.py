import argparse
parser = argparse.ArgumentParser() # Instantiate parser

# Configuration for drop measures
parser.add_argument("--drop_follow_up", action = 'store_true', help = "Drops follow_up if flag is added to action, otherwise all measures included") # Add flags
parser.add_argument("--drop_indicat_prescript", action = 'store_true', help = "Drops indicat/prescript if flag is added to action, otherwise all measures included")
parser.add_argument("--drop_prescriptions", action = 'store_true', help = "Drops prescriptions if flag is added to action, otherwise all measures included") 
parser.add_argument("--drop_reason", action = 'store_true', help = "Drops reason if flag is added to action, otherwise all measures included") 

args = parser.parse_args() # Stores arguments in 'args'

drop_follow_up = args.drop_follow_up # extracts arguments
drop_indicat_prescript = args.drop_indicat_prescript
drop_prescriptions = args.drop_prescriptions
drop_reason = args.drop_reason

# Configuration for date input
parser.add_argument("--start_intv", help="Interval start date")
start_intv = args.start_intv
