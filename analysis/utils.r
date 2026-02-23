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

read_write <- function(read_or_write, path, test = config$test, file_type = config$file_type, df = NULL, dtype = NULL, ...) {
  
  # Add '_test' suffix to path if test flag is TRUE
  if (test) {
    path <- paste0(path, "_test")
  }
  print(path)
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

# Helper function to create and save decile plots
create_and_save_decile_plot <- function(group_name, measures_subset, plots_dir) {
  # Create the plot
  plot <- ggplot(
    filter(practice_deciles, measure %in% measures_subset),
    aes(
      x = interval_start, y = rate_per_1000,
      group = factor(decile),
      linetype = decile,
      color = decile
    )
  ) +
    geom_line() +
    scale_linetype_manual(values = line_types) +
    scale_color_manual(values = line_colors) +
    labs(
      title = glue("Decile Charts for {plots_dir}_rate_mp6"),
      x = "Interval Start",
      y = "Rate per 1000"
    ) +
    facet_wrap(vars(measure), scales = "free_y") +
    theme_bw() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  # Save the plot
  filename <- glue("{plots_dir}/decile_chart_appt_{group_name}_rate_mp6.png")

  ggsave(filename, plot = plot, width = 20, height = 12, dpi = 400)
}

summarise_demographics_rate_zero <-function(df, demo_var) {

  # Filter to relevant demographic measures
  df <- filter(df, grepl(paste0("_", demo_var, "$"), measure))
  # Remove demo_Var suffix from measure names to match group definitions
  df <- df %>%
    mutate(measure = sub(paste0("_", demo_var, "$"), "", measure))
  
  # Sum up populations of each age for rate_zero vs non_zero practices
  practice_measures <- df %>%
    group_by(measure, .data[[demo_var]], rate_zero) %>%
    summarise(
      numerator_midpoint6 = sum(numerator_midpoint6, na.rm = TRUE),
      list_size_midpoint6 = sum(list_size_midpoint6, na.rm = TRUE),
    ) %>%
    mutate(rate_per_1000 = (numerator_midpoint6 / list_size_midpoint6) * 1000) %>%
    ungroup()

  # Export measure-demo_var table
  output_table_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/measure~{demo_var}") # Cant release as practice level
  read_write("write", output_table_path, df = practice_measures, file_type = "csv")

  # Filter to rsv and flu specific measures only for plotting
  practice_measures <- filter(practice_measures, grepl("rsv|flu", measure))

  # Create facet bar plot of list_sizes for each demographic group
  ggplot(practice_measures, aes(x = as.factor(rate_zero), y = list_size_midpoint6, fill = .data[[demo_var]])) +
    geom_bar(position = 'dodge', stat = "identity") +
    theme(axis.text.x = element_text(angle = 90, hjust = 1)) +
    facet_wrap(vars(measure), scales = "free_y") +
    labs(title = "Yearly Measures Analysis", x = "Zero Rate Indicator", y = "List Size")

  # Save plot
  output_plot_path <- glue("output/{config$group}_measures_{config$set}{config$appt_suffix}{config$agg_suffix}/bar_plot_{demo_var}{config$test_suffix}.png")
  ggsave(output_plot_path)
}