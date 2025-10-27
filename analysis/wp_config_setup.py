# This script sets up the configuration for the analysis pipeline.
# It includes the command-line argument options to customize the behaviour of each action.

import argparse
parser = argparse.ArgumentParser() # Instantiate parser

# ----------------- Parse user arguments -------------------------------

# Configuration for add measures
parser.add_argument("--add_indicat_prescript", action = 'store_true', help = "Adds indicat/prescript if flag is added to action.")
parser.add_argument("--add_prescriptions", action = 'store_true', help = "Adds prescriptions if flag is added to action.") 
parser.add_argument("--add_reason", action = 'store_true', help = "Adds reason if flag is added to action.") 
parser.add_argument("--demograph_measures", action= 'store_true', help = "Sets measures defaults to demographic-level subgroups")
parser.add_argument("--practice_measures", action= 'store_true', help = "Sets measures defaults to practice-level subrgoups")
parser.add_argument("--comorbid_measures", action= 'store_true', help = "Sets measures defaults to comorbidity-level subgroups")
parser.add_argument("--use_csv", action = 'store_true', help = "Uses csv instead of arrow for ease of file inspection")

# Configuration for interval date input
parser.add_argument("--start_intv", help="Interval start date")
parser.add_argument("--test", action= 'store_true', help = "Sets lowest time intervals for lightweight testing")

args = parser.parse_args() # Stores arguments in 'args'

# ----------------- Configuration of constants for pipeline -------------------

# Configure dates
args.study_end_date = "2025-03-31"
args.pandemic_start = "2020-03-23"
args.pandemic_end = "2021-07-19"
if args.test:
    args.pandemic_start = "2017-03-01"
    args.pandemic_end = "2018-05-17"
args.n_years = 10
args.dtype_dict = {'measure': 'category', 'interval_start' : 'string', 'numerator' : 'int64', 
        'denominator' : 'int64'}

args.dtype_dict = {'measure': 'category', 'interval_start' : 'string', 'numerator' : 'int64', 
        'denominator' : 'int64'}

if args.demograph_measures:
    args.group = 'demograph'
    args.dtype_dict.update(
        {'age' : 'category', 'sex' : 'category', 'ethnicity' : 'string', 
        'ethnicity_sus': 'string', 'imd_quintile' : 'int8', 'carehome' : 'category',
        'region' : 'category', 'rur_urb_class' : 'Int8'}
    )
elif args.practice_measures:
    args.group = 'practice'
    args.dtype_dict.update({"practice_pseudo_id": "int16"}) # range of int16 is -32768 to 32767

elif args.comorbid_measures:
    args.group = 'comorbid'
    args.dtype_dict.update({'age' : 'category', 'comorbid_chronic_resp' : 'bool', 'comorbid_copd': 'bool',
        'comorbid_asthma': 'bool', 'comorbid_dm': 'bool', 'comorbid_htn': 'bool', 'comorbid_immuno': 'bool', 'vax_flu_12m': 'bool',
        'vax_covid_12m': 'bool', 'vax_pneum_12m': 'bool'
        })    

if args.use_csv:
    args.file_type = 'csv'
else:
    args.file_type = 'arrow'