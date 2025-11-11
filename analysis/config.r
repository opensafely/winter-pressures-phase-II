# This script sets up the configuration for the analysis pipeline.
# It includes the command-line argument options to customize the behaviour of each action.

library(optparse)

# ----------------- Parse user arguments -------------------------------

# Define list of options
option_list <- list(
  make_option("--add_indicat_prescript", action = "store_true",
              default = FALSE, help = "Adds indicat/prescript if flag is added to action."),
  make_option("--add_prescriptions", action = "store_true",
              default = FALSE, help = "Adds prescriptions if flag is added to action."),
  make_option("--add_reason", action = "store_true",
              default = FALSE, help = "Adds reason if flag is added to action."),
  make_option("--demograph_measures", action = "store_true",
              default = FALSE, help = "Sets measures defaults to demographic-level subgroups."),
  make_option("--practice_measures", action = "store_true",
              default = FALSE, help = "Sets measures defaults to practice-level subgroups."),
  make_option("--comorbid_measures", action = "store_true",
              default = FALSE, help = "Sets measures defaults to comorbidity-level subgroups."),
  make_option("--start_intv", type = "character", default = NULL,
              help = "Interval start date."),
  make_option("--test", action = "store_true",
              default = FALSE, help = "Sets lowest time intervals for lightweight testing."),
  make_option("--use_csv", action = "store_true", default = FALSE,
              help = "Use CSV files instead of Arrow for reading/writing data."),
  make_option("--set", type = "character",
              default = FALSE, help = "Choose set of measures between 1) all 2) subset2")
)

# Parse options
parser <- OptionParser(option_list = option_list)
args <- parse_args(parser)

# ----------------- Configuration of constants for pipeline -------------------

# Manually add other configuration parameters
args$study_end_date <- "2025-03-31"
args$n_years <- 10


if (args$demograph_measures){
    args$group = 'demograph'
} else if (args$practice_measures){
    args$group = 'practice'
} else if (args$comorbid_measures){
    args$group = 'comorbid'
}

if (args$use_csv) {
    args$file_type <- "csv"
} else {
    args$file_type <- "arrow"
}
