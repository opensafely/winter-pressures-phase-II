library(dplyr)
library(tidyr)
library(glue)
library(readr)
library(readr)
library(arrow)

# Midpoint rounding function
# Args:
#   x: Numeric vector to be rounded
#   to: The rounding base (default is 6)
# Returns:
#   Numeric vector rounded to the nearest multiple of 'to'
roundmid_any <- function(x, to = 6) {
  ceiling(x / to) * to - (floor(to / 2) * (x != 0))
}

# Function to round specified columns in a dataframe
# Args:
#   df: Dataframe containing the columns to be rounded
#   cols_to_round: Character vector of column names to be rounded
# Returns:
#   Dataframe with specified columns rounded to the nearest multiple of 6
round_columns <- function(df, cols_to_round) {
  rounded_df <- df %>%
    # Select required columns and round their values
    mutate(across(all_of(cols_to_round), ~ roundmid_any(.x))) %>%
    # Dynamically rename the rounded columns
    rename_with(~ paste0(., "_midpoint6"), all_of(cols_to_round))

  return(rounded_df)
}

read_write <- function(read_or_write, path, test = args$test, file_type = args$file_type, df = NULL, dtype = NULL, ...) {
  # Add '_test' suffix to path if test flag is TRUE

  if (test) {
    path <- paste0(path, "_test")
  }

  if (read_or_write == "read") {
    if (file_type == "csv") {
      df <- readr::read_csv(paste0(path, ".csv"), ...)
    } else if (file_type == "arrow") {
      df <- arrow::read_feather(paste0(path, ".arrow"))

      # Apply dtype coercion if provided
      if (!is.null(dtype)) {
        for (col in names(dtype)) {
          target_type <- dtype[[col]]
          if (target_type == "bool") {
            # Arrow stores logicals as "T"/"F" strings in R when written from Python with string conversion
            df[[col]] <- df[[col]] == "T"
          } else {
            df[[col]] <- as(df[[col]], target_type)
          }
        }
      }
    }
    return(df)
  }

  if (read_or_write == "write") {
    if (file_type == "csv") {
      # Ensure the parent directory exists before writing the CSV
      out_path <- paste0(path, ".csv")
      out_dir <- dirname(out_path)
      if (!dir.exists(out_dir)) {
        dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
      }
      readr::write_csv(df, out_path, ...)
    } else if (file_type == "arrow") {
      # Ensure the parent directory exists before writing the Arrow file
      out_path <- paste0(path, ".arrow")
      out_dir <- dirname(out_path)
      if (!dir.exists(out_dir)) {
        dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
      }
      # Arrow in R supports logicals directly, no need to convert unless mimicking Python logic
      arrow::write_feather(df, out_path)
    }
  }
}
