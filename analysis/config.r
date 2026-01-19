# This script sets up the configuration for the R analysis pipeline.
# It reads in user command-line arguments and then extracts the appropriate
# configuration settings from config.json based on those arguments.

library(optparse)
library(styler)
library(jsonlite)

# Run >R config.r to lint repo
#styler::style_dir("analysis")

# Load config
config <- fromJSON(file.path(dirname(sys.frame(1)$ofile), "config.json"))

# ----------------- Parse user arguments -------------------------------

# Define list of options
option_list <- list(
  make_option("--add_indicat_prescript",
    action = "store_true",
    default = config$add_indicat_prescript, help = "Adds indicat/prescript if flag is added to action."
  ),
  make_option("--add_prescriptions",
    action = "store_true",
    default = config$add_prescriptions, help = "Adds prescriptions if flag is added to action."
  ),
  make_option("--add_reason",
    action = "store_true",
    default = config$add_reason, help = "Adds reason if flag is added to action."
  ),
  make_option("--demograph_measures",
    action = "store_true",
    default = config$demograph_measures, help = "Sets measures defaults to demographic-level subgroups."
  ),
  make_option("--practice_measures",
    action = "store_true",
    default = config$practice_measures, help = "Sets measures defaults to practice-level subgroups."
  ),
  make_option("--comorbid_measures",
    action = "store_true",
    default = config$comorbid_measures, help = "Sets measures defaults to comorbidity-level subgroups."
  ),
  make_option("--start_intv",
    type = "character", default = config$start_intv,
    help = "Interval start date."
  ),
  make_option("--test",
    action = "store_true",
    default = config$test, help = "Sets lowest time intervals for lightweight testing."
  ),
  make_option("--use_csv",
    action = "store_true", default = config$use_csv,
    help = "Use CSV files instead of Arrow for reading/writing data."
  ),
  make_option("--set",
    type = "character",
    default = config$set, help = "Choose set of measures between 1) all 2) sro 3) resp."
  ),
  make_option("--appt",
    action = "store_true",
    default = config$appt, help = "Restrict measures to those with an appointment in interval"
  )
)

# Parse options
parser <- OptionParser(option_list = option_list)
args <- parse_args(parser)

# ----------------- Configuration of constants for pipeline -------------------

# Set constants from config
args$study_end_date <- config$study_end_date
args$n_years <- config$n_years
args$sro_dict <- config$sro_dict
args$prioritized <- config$prioritized
args$deprioritized <- setdiff(names(args$sro_dict), args$prioritized)
args$file_type <- config$file_type

# Initialize dtype_dict with base (not used in R, but for consistency)
args$dtype_dict <- config$base_dtype_dict

# Apply group-specific configuration
if (args$demograph_measures) {
  group_config <- config$groups$demograph
  args$group <- group_config$group
} else if (args$practice_measures) {
  group_config <- config$groups$practice
  args$group <- group_config$group
} else if (args$comorbid_measures) {
  group_config <- config$groups$comorbid
  args$group <- group_config$group
}

if (args$appt) {
  args$appt_suffix <- "_appt"
}
