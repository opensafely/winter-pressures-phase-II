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
  make_option("--practice_subgroup_measures",
    action = "store_true",
    default = config$practice_subgroup_measures, help = "Sets measures defaults to practice subgroup-level subgroups."
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
  ),
  make_option("--yearly",
    action = "store_true",
    default = config$yearly, help = "Use yearly measures data"
  ),
  make_option("--released", 
    action = "store_true", 
    default = FALSE, help = "Use already released data"
  ),
  make_option("--weekly_agg", 
    action = "store_true", 
    default = config$weekly_agg, help = "Generate weekly aggregates"
  )
)

# Parse options
parser <- OptionParser(option_list = option_list)
args <- parse_args(parser)

# Override config with provided args
args_list <- as.list(args)
for (key in names(args_list)) {
  config[[key]] <- args_list[[key]]
}

# ----------------- Apply conditional logic to config -------------------

# Configure dates (not needed in R)

# Initialize dtype_dict with base (not used in R, but for consistency)
config$dtype_dict <- config$base_dtype_dict

# Apply group-specific configuration
group_selected <- FALSE
for (group in c("demograph", "practice", "comorbid", "practice_subgroup")) {
  group_flag <- paste0(group, "_measures")
  if (config[[group_flag]]) {
    config$group <- group
    config$dtype_dict <- c(config$dtype_dict, config$groups[[group]]$dtype_dict)
    group_selected <- TRUE
    break  # Only one group can be selected
  }
}

if (config$appt) {
  config$appt_suffix <- "_appt"
} 

if (config$yearly) {
  if (config$weekly_agg) {
    config$agg_suffix <- "_weeklyagg"
  } else {
    config$agg_suffix <- "_yearly"
  }
}

if (config$test) {
  config$test_suffix <- "_test"
}

config$deprioritized <- setdiff(names(config$sro_dict), config$prioritized)

if (config$use_csv) {
  config$file_type <- "csv"
}

if (!is.null(config$set)) {
  if (config$set == "sro") {
    config$pipeline_measures <- config$measures_list$sro
  } else if (config$set == "resp") {
    config$pipeline_measures <- config$measures_list$resp
  } else if (config$set == "appts_table") {
    config$pipeline_measures <- config$measures_list$appts_table
  }
}
