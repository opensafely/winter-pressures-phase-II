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

for (i in seq_along(paths)) {
  df <- read_csv(paths[i])
  
  # Split by status
  df <- df %>%
    mutate(
      status = str_extract(measure, paste(statuses, collapse = "|")),
      measure = str_remove(measure, paste(status, collapse = "|"))
      ) %>%
    mutate(
      measure = str_remove(measure, "_$")
      )
  
  status_df <- df %>%
    pivot_wider(names_from = status, values_from = numerator)
  
  colnames(status_df)[which(names(status_df) == "NA")] <- "numerator"
  
  status_df <- status_df %>%
  select(measure, numerator, everything())
  
  write_csv(status_df, glue("output/appointments/app_pivot_table_{i}.csv"))
  rm(df, status_df)
}

