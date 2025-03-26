import argparse
parser = argparse.ArgumentParser() # Instantiate parser

# Configuration for add measures
parser.add_argument("--add_indicat_prescript", action = 'store_true', help = "Adds indicat/prescript if flag is added to action.")
parser.add_argument("--add_prescriptions", action = 'store_true', help = "Adds prescriptions if flag is added to action.") 
parser.add_argument("--add_reason", action = 'store_true', help = "Adds reason if flag is added to action.") 
parser.add_argument("--patient_measures", action= 'store_true', help = "Sets measures defaults to patient-level subgroups")
parser.add_argument("--practice_measures", action= 'store_true', help = "Sets measures defaults to practice-level subrgoups")

# Configuration for interval date input
parser.add_argument("--start_intv", help="Interval start date")
parser.add_argument("--test", action= 'store_true', help = "Sets lowest time intervals for lightweight testing")

# Configuration for processing
parser.add_argument("--comorbid", action = 'store_true', help = "Sets aggregation level to comorbidities")

args = parser.parse_args() # Stores arguments in 'args'

# Extract args
add_indicat_prescript = args.add_indicat_prescript
add_prescriptions = args.add_prescriptions
add_reason = args.add_reason
patient_measures = args.patient_measures
practice_measures = args.practice_measures
start_intv = args.start_intv
test = args.test
comorbid = args.comorbid