# Processing script for appt report pivot tables

library(tidyverse)
library(glue)

statuses <- c('Booked', 'Arrived', 'DidNotAttend', 'InProgress', 'Finished',
              'Requested', 'Blocked', 'Visit', 'Waiting', 'CancelledbyPatient',
              'CancelledbyUnit', 'CancelledbyOtherService', 'NoAccessVisit',
              'CancelledDueToDeath', 'PatientWalkedOut')

paths <- c(
  "output/appointments/app_measures_1.csv",
  "output/appointments/app_measures_2.csv",
  "output/appointments/app_measures_3.csv",
  "output/appointments/app_measures_4.csv"
)

roundmid_any <- function(x, to=6){
  ceiling(x/to)*to - (floor(to/2)*(x!=0))
}

# Apply midpoint 6 rounding
for (i in seq_along(paths)) {
  df <- read_csv(paths[i])
  df <- df %>% 
    mutate(across(c(ratio,numerator,denominator), roundmid_any))
  write_csv(df, glue("output/appointments/app_measures_rounded_{i}.csv"))
  remove(df)
}

# Reformat to wide, with midpoint 6 rounding 
for (i in seq_along(paths)) {
  df <- read_csv(paths[i])
  # Round to midpoint 6
  df <- df %>% 
    mutate(across(c(ratio,numerator,denominator), roundmid_any))
  
  # Split by status
  df <- df %>%
    mutate(
      status = str_extract(measure, paste(statuses, collapse = "|")),
      measure = str_remove(measure, paste(status, collapse = "|"))
      ) %>%
    mutate(
      measure = str_remove(measure, "_$")
      )
  
  df <- df %>%
    select(- c(interval_end, ratio))
  
  status_df <- df %>%
    pivot_wider(names_from = status, values_from = numerator)
  
  write_csv(status_df, glue("output/appointments/app_pivot_table_{i}.csv"))
  rm(df, status_df)
}

