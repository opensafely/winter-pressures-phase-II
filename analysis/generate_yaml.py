#TODO: 
# 1. Add support for .csv.gz measures
"""
Description: 
- This script generates the YAML file for the project.
- It iteratively generates actions for practice/demographic/comorbidity measures, split across many years.
- It also generates test actions for each action.

Usage:
- python generate_yaml.py

Output:
- project.yaml
"""

from datetime import datetime, timedelta
from utils import generate_annual_dates
from wp_config_setup import args

dates = generate_annual_dates(args.study_end_date, args.n_years)

# --- YAML HEADER ---

yaml_header = """
version: '3.0'

expectations:
  population_size: 1000

actions:
"""

# ------- YAML MEASURES --------------------------------------------

# Patient and practice measures flags to loop
flags = ["practice_measures", "demograph_measures", "comorbid_measures"]

# Temple for measures generation, for each combination of patient/practice measure and start_intv date
yaml_measures_template = """
  generate_{flag}_{date}:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/{flag}/{flag}_{date}.arrow
      --
      --{flag}
      --start_intv {date}
    outputs:
      highly_sensitive:
        dataset: output/{flag}/{flag}_{date}.arrow
"""

yaml_measures = ""
needs = {}

# Iterate over flags
for flag in flags:
  needs[flag] = []

  # Iterate over dates and generate yaml list of needs for each combination
  for date in dates:
    yaml_measures += yaml_measures_template.format(flag = flag, date = date)
    needs[flag].append(f"generate_{flag}_{date}")

  # Join list into string for each flag
  needs[flag] = ", ".join(needs[flag])

yaml_measures_test = '''
  # --------------- TEST ACTIONS ------------------------------------------

  generate_demograph_measures_test:
    run: ehrql:v1 generate-measures analysis/wp_measures.py 
      --output output/demograph_measures/demograph_measures_{start_date}_test.arrow
      --
      --demograph_measures
      --start_intv {start_date}
      --test
    outputs:
      highly_sensitive:
        dataset: output/demograph_measures/demograph_measures_{start_date}_test.arrow
  generate_practice_measures_test:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/practice_measures/practice_measures_{start_date}_test.arrow
      --
      --practice_measures
      --start_intv {start_date}
      --test
    outputs:
      highly_sensitive:
        dataset: output/practice_measures/practice_measures_{start_date}_test.arrow
  generate_comorbid_measures_test:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/comorbid_measures/comorbid_measures_{start_date}_test.arrow
      --
      --comorbid_measures
      --start_intv {start_date}
      --test
    outputs:
      highly_sensitive:
        dataset: output/comorbid_measures/comorbid_measures_{start_date}_test.arrow
'''
yaml_measures_test = yaml_measures_test.format(start_date = dates[0])

# --------------- YAML APPT REPORT ------------------------------------------
yaml_appt_report = ""

appt_dates = {
    1: datetime.strptime("2023-07-01", "%Y-%m-%d").date(),
    2: datetime.strptime("2023-12-01", "%Y-%m-%d").date(),
    3: datetime.strptime("2018-07-01", "%Y-%m-%d").date(),
    4: datetime.strptime("2018-12-01", "%Y-%m-%d").date()
}

appt_needs = []

yaml_appt_template = """
  generate_app_measures_intv_{key}:
     run: ehrql:v1 generate-measures analysis/appointments/app_measures.py
      --output output/appointments/app_measures_{key}.csv 
      -- 
      --start_intv {appt_date}
     outputs:
       moderately_sensitive:
         dataset: output/appointments/app_measures_{key}.csv
 """ 

for key, value in appt_dates.items():
    yaml_appt_report += yaml_appt_template.format(key = key, appt_date = value)
    appt_needs.append(f"generate_app_measures_intv_{key}")

appt_list = ", ".join(appt_needs)

yaml_appt_processing_template = """
  generate_app_processing:
     run: r:v2 analysis/appointments/app_processing.r
     needs: [{appt_list}]
     outputs:
       moderately_sensitive:
         table_rounded: output/appointments/app_measures_rounded_*.csv
"""
yaml_appt_processing = yaml_appt_processing_template.format(appt_list=appt_list)

yaml_appt_report = yaml_appt_report + yaml_appt_processing
yaml_appt_report += " \n # --------------- PROCESSING ------------------------------------------\n"

groups = ["demograph", "practice", "comorbid"]
yaml_processing_template = """
  generate_freq_table_{group}{test_suffix}:
    run: python:v2 analysis/freq_table.py --{group}_measures  {test_flag}
    needs: [{needs}{test_suffix}]
    outputs:
      moderately_sensitive:
        freq_table: output/{group}_measures/freq_table_{group}{test_suffix}.csv

  generate_pre_processing_{group}{test_suffix}:
    run: python:v2 analysis/pre_processing.py --{group}_measures {test_flag}
    needs: [{needs}{test_suffix}]
    outputs:
      highly_sensitive:
        measures: output/{group}_measures/proc_{group}_measures{test_suffix}.arrow
  generate_rounding_{group}{test_suffix}:
    run: r:v2 analysis/round_measures.r --{group}_measures  {test_flag}
    needs: [generate_pre_processing_{group}{test_suffix}]
    outputs:
      highly_sensitive:
        rounded_measures: output/{group}_measures/proc_{group}_measures_midpoint6{test_suffix}.arrow
  generate_normalization_{group}{test_suffix}:
    run: python:v2 analysis/normalization.py --{group}_measures {test_flag}
    needs: [generate_rounding_{group}{test_suffix}]
    outputs:
      highly_sensitive:
        practice_level_tables: output/{group}_measures/practice_level_counts{test_suffix}.arrow
      moderately_sensitive:
        seasonal_tables_tables: output/{group}_measures/Results*{test_suffix}.csv

"""
''' TEMPORARILY COMMENTED OUT:

  # Visualisation
  generate_tables_demograph{test_suffix}:
    run: r:v2 analysis/table_generation.r --demograph_measures {test_flag}
    needs: [generate_rounding{test_suffix}]
    outputs:
     moderately_sensitive:
       tables: output/demograph_measures/plots/*_demograph{test_suffix}.csv
       plots: output/demograph_measures/plots/*_demograph{test_suffix}.png
  generate_tables_comorbid{test_suffix}:
    run: r:v2 analysis/table_generation.r --comorbid_measures {test_flag}
    needs: [generate_rounding{test_suffix}]
    outputs:
     moderately_sensitive:
        tables: output/comorbid_measures/plots/*_comorbid{test_suffix}.csv
        plots: output/comorbid_measures/plots/*_comorbid{test_suffix}.png

  generate_deciles_charts{test_suffix}:
    run: >
      r:v2 analysis/decile_charts.r {test_flag}
    needs: [generate_rounding{test_suffix}] 
    outputs:
      moderately_sensitive:
        deciles_charts: output/practice_measures/plots/decile_chart_*_rate_mp6{test_suffix}.png
        deciles_table: output/practice_measures/decile_tables/decile_table_*_rate_mp6{test_suffix}.csv
  generate_deciles_charts_RR{test_suffix}:
    run: >
      r:v2 analysis/decile_charts.r --RR {test_flag}
    needs: [generate_normalization{test_suffix}]
    outputs:
      moderately_sensitive:
        deciles_charts: output/practice_measures/plots/decile_chart_*_RR{test_suffix}.png
        deciles_table: output/practice_measures/decile_tables/decile_table_*_RR{test_suffix}.csv
'''
yaml_processing = ""
yaml_processing_test = ""
for group in groups:
  # Actions for processing real data
  yaml_processing += yaml_processing_template.format(group = group,
                                          needs = needs[f'{group}_measures'],
                                          test_suffix = "",
                                          test_flag = "",)
  
for group in groups:
  # Actions for processing test data
  yaml_processing_test += yaml_processing_template.format(group = group,
                                          needs = f'generate_{group}_measures',
                                          test_suffix = "_test",
                                          test_flag = "--test")

# --- Combine scripts and print file ---
yaml = yaml_header + yaml_measures + yaml_appt_report + yaml_processing + yaml_measures_test + yaml_processing_test

with open("/workspaces/winter-pressures-phase-II/project.yaml", "w") as file:
       file.write(yaml)