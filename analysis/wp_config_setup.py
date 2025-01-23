import argparse
parser = argparse.ArgumentParser() # Instantiate parser

# Configuration for drop measures
parser.add_argument("--drop_follow_up", action = 'store_true', help = "Drops follow_up if flag is added to action, otherwise all measures included") # Add flags
parser.add_argument("--drop_indicat_prescript", action = 'store_true', help = "Drops indicat/prescript if flag is added to action, otherwise all measures included")
parser.add_argument("--drop_prescriptions", action = 'store_true', help = "Drops prescriptions if flag is added to action, otherwise all measures included") 
parser.add_argument("--drop_reason", action = 'store_true', help = "Drops reason if flag is added to action, otherwise all measures included") 
parser.add_argument("--patient_measures", action= 'store_true', help = "Sets measures defaults to patient-level subgroups")
parser.add_argument("--practice_measures", action= 'store_true', help = "Sets measures defaults to practice-level subrgoups")

# Configuration for interval date input
parser.add_argument("--start_intv", help="Interval start date")

args = parser.parse_args() # Stores arguments in 'args'

# Extract args
drop_follow_up = args.drop_follow_up 
drop_indicat_prescript = args.drop_indicat_prescript
drop_prescriptions = args.drop_prescriptions
drop_reason = args.drop_reason
patient_measures = args.patient_measures
practice_measures = args.practice_measures
start_intv = args.start_intv
