library(dplyr)
library(tidyr)
library(glue)
library(readr)

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
  print(colnames(df))
  # print unique values in columns
  for (col in cols_to_round) {
    cat(glue::glue("Unique values in {col}:\n"))
    print(typeof(df[[col]]))
    print(unique(df[[col]]))
    cat("\n")
  }
  rounded_df <- df %>%
    # Select required columns and round their values
    mutate(across(all_of(cols_to_round), ~ roundmid_any(.x))) %>%
    # Dynamically rename the rounded columns
    rename_with(~ paste0(., "_midpoint6"), all_of(cols_to_round))

  return(rounded_df)
}