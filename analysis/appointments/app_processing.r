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

# A function to apply midpoint rounding as per OS documentation on disclosure control
roundmid_any <- function(x, to=6){
  ceiling(x/to)*to - (floor(to/2)*(x!=0))
}

# Apply midpoint 6 rounding, generate pivot tables
for (i in seq_along(paths)) {
  
  df <- read_csv(paths[i])
  
  # Round to midpoint 6 and save
  rounded_df <- df %>% 
    mutate(across(c(ratio,numerator,denominator), roundmid_any))%>%
    mutate(ratio = numerator / denominator)%>%
    rename(
      midpoint_rounded_numerator = numerator,
      midpoint_rounded_denominator = denominator
    )
  write_csv(rounded_df, glue("output/appointments/app_measures_rounded_{i}.csv"))

  # Split by status
  df <- rounded_df %>%
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
    rename(
      numerator = midpoint_rounded_numerator,
      denominator = midpoint_rounded_denominator) %>%
    pivot_wider(names_from = status, values_from = numerator)
  
  write_csv(status_df, glue("output/appointments/app_pivot_table_{i}.csv"))
  rm(rounded_df, df, status_df)
}

