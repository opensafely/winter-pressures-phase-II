# USAGE: Rscript analysis/stat_test.r
# Options:
# --test: Use lightweight test data as input
# --practice_measures OR --demograph_measures OR --comorbid_measures flags to select pipeline

library(dplyr)
library(purrr)
library(broom)
library(lme4)
library(stringr)
source("analysis/utils.r")
source("analysis/config.r")

practice_counts_df <- read_write('read', glue("output/{args$group}_measures/Results_weighted_long"), file_type = 'csv')

practice_counts_df$rate_per_1000 <- (practice_counts_df$numerator_midpoint6_sum / practice_counts_df$list_size_midpoint6_sum)*1000
practice_counts_df$major_season <- ifelse(practice_counts_df$season == 'Jun-Jul', "Summer", "Winter")

# Prepare a list to store results
results_list <- list()

for (practice in unique(practice_counts_df$practice_pseudo_id)) {
  
  # Subset the data for this practice
  df_sub <- filter(practice_counts_df, practice_pseudo_id == practice)

  model <- glm(
    numerator_midpoint6_sum ~ major_season * measure,
    offset = log1p(list_size_midpoint6_sum),
    family = poisson,
    data = df_sub
  )
  
  # Extract tidy results
  tidy_model <- tidy(model) %>%
    mutate(
      rate_ratio = exp(estimate),  # exponentiate to get rate ratio
      practice_id = practice       # add practice id
    ) %>%
    select(practice_id, term, rate_ratio, p.value)
  
  results_list[[as.character(practice)]] <- tidy_model
}

# Combine all practices into one table
results_table <- bind_rows(results_list)
results_table$rate_ratio <- round(results_table$rate_ratio, 3)
results_table$signif <- ifelse(results_table$p.value < 0.05, 1, 0)
results_table <- results_table %>%
  mutate(
    measure = str_extract(term, paste(unique(practice_counts_df$measure), collapse = "|"))
  )
read_write("write", "output/{args$group}_measures/summary_results", file_type = "csv", df = results_table)

# Define sets of terms
measure_terms <- paste0("measure", unique(practice_counts_df$measure))
interaction_terms <- paste0("major_seasonWinter:measure", unique(practice_counts_df$measure))

# Extract measure coefficients
df_coefs <- filter(results_table, term %in% measure_terms) %>%
  mutate(measure = str_extract(term, paste(unique(practice_counts_df$measure), collapse = "|")))

# Extract winter coefficients
df_winter <- filter(results_table, term == "major_seasonWinter")

# Extract measure-winter interaction coefficients
df_interactions <- filter(results_table, term %in% interaction_terms) %>%
  mutate(measure = str_extract(term, paste(unique(practice_counts_df$measure), collapse = "|")))

# Join step-by-step, adding suffixes to each column for identification
results_wide <- df_coefs %>%
  rename_with(~ paste0(.x, "_coef"), -c(practice_id, measure)) %>%
  left_join(df_winter %>%
              rename_with(~ paste0(.x, "_winter"), -practice_id),
            by = "practice_id") %>%
  left_join(df_interactions %>%
              rename_with(~ paste0(.x, "_interact"), -c(practice_id, measure)),
            by = c("practice_id", "measure"))

# RR_measure in winter = RR_measure * RR_winter * RR_measure interacting with winter
results_wide$total_RR = results_wide$rate_ratio_coef * results_wide$rate_ratio_winter * results_wide$rate_ratio_interact

# Summarise average total RR across practices for a measure
results_agg <- results_wide %>%
  group_by(measure) %>%
  summarise(
    RR_median = median(total_RR),
    RR_lowerq = quantile(total_RR, 0.25),
    RR_uppperq = quantile(total_RR, 0.75),
    #signif_count = sum(signif), WHICH COEFS ARE WE TESTING??
    test_count = n()
  ) #%>%
  #mutate(signif_propn = (signif_count/test_count)*100)

read_write("write", "output/{args$group}_measures/summary_results_agg", file_type = "csv", df = results_agg)
