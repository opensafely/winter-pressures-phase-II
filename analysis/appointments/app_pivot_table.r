library(tidyverse)

statuses <- c('Booked', 'Arrived', 'DidNotAttend', 'InProgress', 'Finished',
              'Requested', 'Blocked', 'Visit', 'Waiting', 'CancelledbyPatient',
              'CancelledbyUnit', 'CancelledbyOtherService', 'NoAccessVisit',
              'CancelledDueToDeath', 'PatientWalkedOut')

df <- read_csv("output/appointments/app_summary.csv")

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

write_csv(status_df, "output/appointments/status_summary.csv")
