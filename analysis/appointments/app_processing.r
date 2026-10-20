# Processing script for appt report pivot tables

library(tidyverse)
library(glue)
library(readr)
library(dplyr)
source("analysis/utils.r")

statuses <- c(
  "Booked", "Arrived", "DidNotAttend", "InProgress", "Finished",
  "Requested", "Blocked", "Visit", "Waiting", "CancelledbyPatient",
  "CancelledbyUnit", "CancelledbyOtherService", "NoAccessVisit",
  "CancelledDueToDeath", "PatientWalkedOut"
)

paths <- c(
  "output/appointments/app_measures_1.csv",
  "output/appointments/app_measures_2.csv",
  "output/appointments/app_measures_3.csv",
  "output/appointments/app_measures_4.csv"
)

# Loop over each appts file
for (i in seq_along(paths)) {
  df <- read_csv(paths[i])
  # Round and save the numerator and denominator columns
  round_columns(df, cols_to_round = c("numerator", "denominator")) %>%
    # Recalculate ratio based on rounded values
    mutate(ratio = numerator_midpoint6 / denominator_midpoint6) %>%
    rename(
      midpoint_rounded_numerator = numerator_midpoint6,
      midpoint_rounded_denominator = denominator_midpoint6
    ) %>%
    # Save the rounded dataframe to a new CSV file
    write_csv(glue("output/appointments/app_measures_rounded_{i}.csv"))
}
