library(dplyr)
library(tidyr)
library(glue)
library(readr)
library(readr)
library(arrow)
library(ggplot2)

roundmid_any <- function(x, to = 6) {
  # Midpoint rounding function
  # Args:
  #   x: Numeric vector to be rounded
  #   to: The rounding base (default is 6)
  # Returns:
  #   Numeric vector rounded to the nearest multiple of 'to'

  ceiling(x / to) * to - (floor(to / 2) * (x != 0))
}

round_columns <- function(df, cols_to_round) {
  # Function to round specified columns in a dataframe
  # Args:
  #   df: Dataframe containing the columns to be rounded
  #   cols_to_round: Character vector of column names to be rounded
  # Returns:
  #   Dataframe with specified columns rounded to the nearest multiple of 6

  rounded_df <- df %>%
    # Select required columns and round their values
    mutate(across(all_of(cols_to_round), ~ roundmid_any(.x))) %>%
    # Dynamically rename the rounded columns
    rename_with(~ paste0(., "_midpoint6"), all_of(cols_to_round))

  return(rounded_df)
}

read_write <- function(read_or_write, path, test = config$test, file_type = config$file_type, df = NULL, dtype = NULL, ...) {
  # Function to read or write dataframes in either CSV or Arrow format, with optional test suffix and dtype coercion for Arrow
  # Args:
  #   read_or_write: String indicating whether to read or write ("read" or "write")
  #   path: The file path for reading or writing
  #   test: Boolean indicating whether to add a "_test" suffix to the file path (default is config$test)
  #   file_type: String indicating the file type ("csv" or "arrow", default is config$file_type)
  #   df: Dataframe to be written (required if read_or_write is "write")
  #   dtype: Optional named list of column names and target data types for coercion when reading Arrow files (e.g. list(col1 = "bool", col2 = "numeric"))
  
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

create_and_save_decile_plot <- function(chart_type, deciles_df, group_name, measures_subset, plots_dir, y_var, x_var = "interval_start", season="") {
  # Function to create and save a decile plot for a given group of measures and season
  # Args:
  #   group_name: Name of the measure group (e.g. "prioritized", "deprioritized", "other")
  #   measures_subset: Character vector of measure names to include in the plot
  #   plots_dir: Directory where the plot will be saved
  #   y_var: The variable to plot on the y-axis (e.g. "rate_per_1000_mp6" or "RR_prev_summr")
  #   x_var: The variable to plot on the x-axis (default is "interval_start")
  #   season: The season for which to create the plot

  # Format season name
  if (season != "") {
    season <- paste0("_", season)
  }
  print(x_var)

  if (chart_type == "decile"){
    # Create the plot
    p <- ggplot(
      filter(deciles_df, measure %in% measures_subset),
      aes(
        x = !!sym(x_var), y = !!sym(y_var),
        group = factor(decile),
        linetype = decile,
        color = decile
      )
    ) +
      geom_line() +
      scale_linetype_manual(values = line_types) +
      scale_color_manual(values = line_colors) +
      labs(
        title = glue("Decile Charts for {plots_dir}_{y_var}{season}"),
        x = x_var,
        y = y_var
      ) +
      facet_wrap(vars(measure), scales = "free_y") +
      theme_bw() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
  }
  else if (chart_type == "dotplot") {
    p <- ggplot(
      filter(deciles_df, measure %in% measures_subset),
      aes(
        x = factor(!!sym(x_var)), y = !!sym(y_var), fill = factor(decile)
      )
    ) +
      geom_dotplot(binaxis = "y", stackdir = "center", dotsize = 1) +
      labs(
        title = glue("Decile dotplot for {plots_dir}_{y_var}{season}"),
        x = x_var,
        y = y_var
      ) +
      facet_wrap(vars(measure), scales = "free_y") +
      scale_fill_manual(
      values = c(
        "d1" = "black",
        "d2" = "black",
        "d3" = "black",
        "d4" = "black",
        "d5" = "red",
        "d6" = "black",
        "d7" = "black",
        "d8" = "black",
        "d9" = "black",
        "d10" = "black"
      ))
  }
  else if (chart_type == "seasonal lineplot") {

    deciles_df <- deciles_df %>%
      mutate(
        season_year_start = if_else(
          month(interval_start) >= 6,
          year(interval_start),
          year(interval_start) - 1
        ),
        season_year = glue("{season_year_start}/{substr(season_year_start + 1, 3, 4)}"),
        season_year = factor(season_year),
        season_x = make_date(
          year = if_else(month(interval_start) >= 6, 2000L, 2001L),
          month = month(interval_start),
          day = day(interval_start)
        )
      )

    p <- ggplot(
      filter(deciles_df, (measure %in% measures_subset) & (decile == "d5")),
      aes(
        x = season_x,
        y = !!sym(y_var),
        group = season_year,
        color = season_year
      )
    ) +
      geom_line() +
      scale_x_date(
        date_breaks = "1 month",
        date_labels = "%b",
        limits = as.Date(c("2000-06-01", "2001-05-31"))
      ) +
      labs(
        title = glue("Seasonal Line Plot for {plots_dir}_{y_var}{season}"),
        x = "Month",
        y = y_var,
        color = "Season year"
      ) +
      facet_wrap(vars(measure), scales = "free_y") +
      theme_bw() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
  }

    # Save the plot
    filename <- glue("{plots_dir}/{chart_type}_chart_{group_name}{season}_{y_var}.png")
    ggsave(filename, plot = p, width = 20, height = 12, dpi = 400)
}

summarise_demographics_rate_zero <-function(df, demo_var) {
  # Function to summarise demographic characteristics of practices with zero rates vs non-zero rates for a given measure
  # Args:
  #   df: Dataframe containing practice-level measures and demographic variables
  #   demo_var: The demographic variable to summarise (e.g. "age_band or "imd_decile")

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
    mutate(rate_per_1000_mp6 = (numerator_midpoint6 / list_size_midpoint6) * 1000) %>%
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

format_measures_for_plotting <- function(df, set, subset) {
  # Function to format measure names for plotting based on the set and subset
  # Args:
  #   df: Dataframe containing the measures to be formatted
  #   set: The set of measures (e.g. "sro" or "resp")
  #   subset: The subset of measures (e.g. "tests", "other", "specific", "sensitive", or "all")

    if (set == "sro") {
      if (subset == "tests"){
        filtered_measures <- c("sodium_test", "alt_test", "chol_test", "sys_bp_test", "rbc_test", "hba1c_test", "cvd_10yr", "thy_test")
      }
      else if (subset == "other") {
        filtered_measures <- c("asthma_review", "copd_review", "sro_prioritized", "sro_deprioritized")
      }
      else if (subset ==  "all") {
        filtered_measures <- c("sodium_test", "alt_test", "chol_test", "sys_bp_test", "rbc_test", "hba1c_test", "cvd_10yr", "thy_test",
                              "asthma_review", "copd_review", "sro_prioritized", "sro_deprioritized")
      }
        df <- df %>%
            # Filter to measures of interest for plotting
            filter(measure %in% filtered_measures) %>%
            # Rename measures
            mutate(measure = case_when(
                measure == "sodium_test" ~ "Sodium",
                measure == "alt_test" ~ "ALT",
                measure == "chol_test" ~ "Cholesterol",
                measure == "sys_bp_test" ~ "BP Systolic",
                measure == "rbc_test" ~ "RBC",
                measure == "hba1c_test" ~ "HbA1c",
                measure == "cvd_10yr" ~ "10 yr CVD",
                measure == "thy_test" ~ "Thyroid",
                measure == "asthma_review" ~ "Asthma Revw",
                measure == "copd_review" ~ "COPD Revw",
                measure == "sro_prioritized" ~ "High Priority tests",
                measure == "sro_deprioritized" ~ "Low Priority tests",
                TRUE ~ measure
            ))
    }
    else if (set == "resp") {
      if (subset == "specific"){
        filtered_measures <- c("flu_specific", "rsv_specific")
      }
      else if (subset == "sensitive") {
        filtered_measures <- c("overall_resp_sensitive","flu_sensitive", "rsv_sensitive")
      }
      else if (subset ==  "all") {
        filtered_measures <- c("overall_resp_sensitive", "flu_sensitive", "rsv_sensitive", "flu_specific", "rsv_specific")
      }
        df <- df %>%
            # Filter to measures of interest for plotting
            filter(measure %in% filtered_measures) %>%
            # Rename measures
            mutate(measure = case_when(
                measure == "overall_resp_sensitive" ~ "Overall",
                measure == "flu_sensitive" ~ "Flu Sensitive",
                measure == "rsv_sensitive" ~ "RSV Sensitive",
                measure == "flu_specific" ~ "Flu Specific",
                measure == "rsv_specific" ~ "RSV Specific",
                TRUE ~ measure
            )) %>%
            # Reorder measures
            mutate(measure = factor(measure, levels = c("Overall", "Flu Sensitive", "RSV Sensitive", "Flu Specific", "RSV Specific")))     
    }
    return(df)
}

format_colours_for_plotting <- function(df, colour_var, y_var = NULL, baseline = NULL) {
  # Function to format line types and colours for plotting based on the colouring variable
  # Args:
  #   df: Dataframe containing the data to be plotted
  #   colour_var: The variable by which the lines will be coloured (e.g. "season", "percentile", or "%_practices")
  #   y_var: The variable being plotted on the y-axis (used for naming conventions when colour_var is "percentile" or "%_practices")
  #   baseline: The baseline category for comparison (used for naming conventions when colour_var is "percentile" or "%_practices")

  if (colour_var == "season") {
    season_order <- c("Sep-Oct", "Nov-Dec", "Jan-Feb", "Mar-Apr", "Jun-Jul")

    full_linetype_mapping <- c(
      "Sep-Oct" = "dashed",
      "Nov-Dec" = "solid",
      "Jan-Feb" = "solid",
      "Mar-Apr" = "dashed",
      "Jun-Jul" = "solid"
    )

    full_colour_mapping <- c(
      "Sep-Oct" = "#00fff7",
      "Nov-Dec" = "#2f00ff",
      "Jan-Feb" = "#76b370",
      "Mar-Apr" = "#ffd500",
      "Jun-Jul" = "#ff0000"
    )

    present_seasons <- intersect(season_order, unique(as.character(df$season)))

    df <- df %>%
      mutate(season = factor(season, levels = present_seasons))

    linetype_mapping <- full_linetype_mapping[present_seasons]
    colour_mapping <- full_colour_mapping[present_seasons]
  } else if (colour_var == "percentile") {
    linetype_mapping <- c(
      "dotted",
      "dashed",
      "solid",
      "dashed",
      "dotted"
    )
    names(linetype_mapping) <- c(
      glue("{y_var}_{baseline}_summr_p01"),
      glue("{y_var}_{baseline}_summr_p25"),
      glue("{y_var}_{baseline}_median"),
      glue("{y_var}_{baseline}_summr_p75"),
      glue("{y_var}_{baseline}_summr_p99")
    )
    colour_mapping <- c(
      "#006eff",
      "#006eff",
      "#006eff",
      "#006eff",
      "#006eff"
    )
    names(colour_mapping) <- names(linetype_mapping)
  } else if (colour_var == "%_practices") {
    linetype_mapping <- c(
      "dashed",
      "solid",
      "dashed"
    )
    names(linetype_mapping) <- c(
      glue("%_{y_var}_{baseline}_summr_<5%"),
      glue("%_{y_var}_{baseline}_summr_=1"),
      glue("%_{y_var}_{baseline}_summr_>5%")
    )
    colour_mapping <- c(
      "#ff3700",
      "#000000",
      "#006eff"
    )
    names(colour_mapping) <- names(linetype_mapping)
  }

  list(linetype_mapping = linetype_mapping, colour_mapping = colour_mapping, df = df)
}

plot_rr_timeseries_by_measure <- function(y_var, colour_var, baseline, weighting, set, subset, representative_season = NULL, appt = FALSE) {
    "
    This function produces a line plot, coloured by season, faceted by measure
    Args:
        df: dataframe containing the results of the rate ratio calculations
        y_var: string name of the variable to plot on the y-axis (e.g. 'RR_prev_summr_mp6')
        colour_var: string name of the variable to colour the lines by {season / percentile / %_practices}
        colour_label: the label for the colour legend
        baseline: the baseline category for comparison
    "
    # Configuration
    if (weighting == "weighted") {
        df_name <- paste(glue("weighted"))
        y_col <- paste(glue("{y_var}_{baseline}_summr_mp6"))
    }
    else if ((weighting == "unweighted") & (colour_var == "season")) {
        df_name <- paste(glue("unweighted_yearly_{baseline}_summer"))
        y_col <- paste(glue("{y_var}_{baseline}_median"))
    }
    else if ((weighting == "unweighted") & (colour_var == "percentile")) {
        df_name <- paste(glue("unweighted_yearly_{baseline}_summer"))
        y_col <- paste(glue("{y_var}_{baseline}_summer"))
    }
    else if ((weighting == "unweighted") & (colour_var == "%_practices")) {
        df_name <- paste(glue("unweighted_yearly_{baseline}_summer"))
        y_col <- paste(glue("%_{y_var}_{baseline}_summer"))
    }
  
    if (appt == TRUE) {
      appt_suffix <- "_appt"
    } else {
      appt_suffix <- ""
    }
  
    # Load results and remove any unnamed columns that may have been added during CSV export
    results_df <- read.csv(glue("output/practice_measures_{set}{appt_suffix}/Results_{df_name}.csv"), check.names = FALSE) 
    results_df <- results_df[, names(results_df) != ""]

    # Remove _appt prefix from measure names for appt restricted df
    if (appt == TRUE) {
      results_df <- results_df %>%
        mutate(measure = sub("^appt_", "", measure))
    }
  
    # Pivot percentiles if colouring by percentile
    if (colour_var == "percentile") {
        results_df <- results_df %>%
            pivot_longer(cols = c(glue("{y_var}_{baseline}_summr_p01"), glue("{y_var}_{baseline}_summr_p25"), glue("{y_var}_{baseline}_median"), glue("{y_var}_{baseline}_summr_p75"), glue("{y_var}_{baseline}_summr_p99")), names_to = "percentile", values_to = as.character(y_col))
        
        # Percentile chart - do we need RD as well?
        results_df <- filter(results_df, season == representative_season)
    }
    else if (colour_var == "%_practices") {
      print(head(results_df))
      print(summary(results_df))
        results_df <- results_df %>%
            pivot_longer(cols = c(glue("%_RR_{baseline}_summr_<5%"), glue("%_RR_{baseline}_summr_=1"), glue("%_RR_{baseline}_summr_>5%")), names_to = "%_practices", values_to = as.character(y_col))
        
        # Take the average across seasons for each year for the %_practices plot
        results_df <- results_df %>%
            group_by(measure, summer_year, `%_practices`) %>%
            summarise(across(all_of(y_col), mean, na.rm = TRUE)) %>%
            ungroup()
    }
  
    # Format measure names for readability
    results_df <- format_measures_for_plotting(results_df, set, subset)
  
    # Format colours for plotting
    format_mappings <- format_colours_for_plotting(results_df, colour_var, y_var = y_var, baseline = baseline)    
    linetype_mapping <- format_mappings$linetype_mapping
    colour_mapping <- format_mappings$colour_mapping
    results_df <- format_mappings$df
  
    line_plot <- results_df %>%
        ggplot(aes(x = summer_year, y = .data[[y_col]], color = .data[[colour_var]], linetype = .data[[colour_var]])) +
        geom_line() +
        geom_point() +
        scale_linetype_manual(values = linetype_mapping) +
        scale_color_manual(values = colour_mapping) +
        labs(title = glue("{y_var} (vs {baseline} summer) Over Time by {colour_var}, {weighting} by practice list size {appt_suffix}"),
            x = "summer baseline year",
            y = y_var) +
        theme_minimal() +
        facet_grid(rows = vars(measure)) +
        theme(legend.title = element_blank())

    return(line_plot)
}

plot_variance_bar_chart <- function(var_type, set, subset = NULL) {
    "This function produces a bar chart of the variance of the pressure metric
    Args:
        var_type: string name of the type of variance to plot (e.g. 'btwn' or 'w.in')
        set: Set of measures (resp or sro)"
    
    # Load variance df
    variance_df <- read.csv(glue("output/practice_measures_{set}/Results_variances.csv"))

    # Format colours for plotting
    format_mappings <- format_colours_for_plotting(variance_df, colour_var = "season")
    linetype_mapping <- format_mappings$linetype_mapping
    colour_mapping <- format_mappings$colour_mapping
    variance_df <- format_mappings$df
  
    # Format measure names for readability
    variance_plot <- format_measures_for_plotting(variance_df, set, subset) %>%
        ggplot(aes(x = measure, y = .data[[glue("var_rate_{var_type}_prac_season_median")]], fill = season)) +
        geom_col(position = position_dodge(width = 0.9)) +
        labs(title = glue("Variance in rate {var_type} practices by Season"),
            x = "Season",
            y = glue("Variance in rate {var_type} practices")) +
        theme_minimal() +
        scale_fill_manual(values = colour_mapping) +
        theme(legend.title = element_blank())
    
    return(variance_plot)
}