# USAGE: Rscript analysis/stat_test.r
# Options:
# --test: Use lightweight test data as input
# --practice_measures OR --demograph_measures OR --comorbid_measures flags to select pipeline

library(dplyr)
library(purrr)
library(broom)
source("analysis/utils.r")
source("analysis/config.r")

practice_counts_df <- read_write('read', glue("output/{args$group}_measures/practice_level_counts"))

# --- 1. Filter data: remove tiny practices / summer zeros ---

df_filtered <- practice_counts_df %>%
  filter(
    !is.na(numerator_midpoint6_sum_prev_summr),
    numerator_midpoint6_sum_prev_summr > 0,  # remove summer zeros if needed
    !is.na(numerator_midpoint6_sum),
    numerator_midpoint6_sum > 0,
  )
print("1- complete")

# --- 2. Pivot to long format for easier GLM per practice ---

df_long <- df_filtered %>%
  mutate(
    numerator = numerator_midpoint6_sum,
    list_size = list_size_midpoint6_sum
  ) %>%
  select(practice_id = practice_pseudo_id, measure, pandemic, season,
         numerator, list_size)
print("2- complete")

# Combine previous summer counts as “winter” (or alternative) if needed
# For simplicity, assume each row = one season per practice

# --- 3. Function to fit per-practice Poisson GLM ---

fit_practice_glm <- function(df) {
  # glm with offset = log(list_size)
  mod <- glm(
    numerator ~ season, #+ pandemic,  # include covariates as needed
    offset = log(list_size),
    family = poisson,
    data = df
  )
  tidy(mod) %>%
    filter(term == "season_labelsummer") %>%
    select(estimate, std.error, p.value)
}
print("3- complete")

# --- 4. Apply per practice + measure ---
results_per_practice <- df_long %>%
  group_by(practice_id, measure) %>%
  nest() %>%
  mutate(glm_res = map(data, fit_practice_glm)) %>%
  unnest(glm_res)

print("4- complete")

# --- 5. Multiple testing adjustment ---
results_per_practice <- results_per_practice %>%
  mutate(p_adj = p.adjust(p.value, method = "BH"),
         signif = p.value < 0.05,
         signif_adj = p_adj < 0.05)

print("5- complete")
# --- 6. Compute proportion significant per measure ---
summary_results <- results_per_practice %>%
  group_by(measure) %>%
  summarise(
    n_practices = n(),
    signif_count = sum(signif),
    signif_adj_count = sum(signif_adj),
    signif_prop = signif_count / n_practices * 100,
    signif_adj_prop = signif_adj_count / n_practices * 100
  )

# --- 7. Optional: round results ---
summary_results <- summary_results %>%
  mutate(across(where(is.numeric), round, 2))

read_write("write", "output/summary_results", file_type = "csv", df = summary_results)
