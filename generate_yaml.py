# TODO:
# Add actions for patient and practice pre_processing files

"""
Description: 
- This script generates the YAML file for the project.
- It iteratively generates measures for each combination of patient/practice measures and interval date.

Usage:
- python generate_yaml.py

Output:
- project.yaml
"""

from datetime import datetime, timedelta
from analysis.utils import generate_annual_dates

# --- YAML HEADER ---

yaml_header = """
version: '3.0'

expectations:
  population_size: 1000

actions:
"""

# --- YAML MEASURES BODY ----

dates = generate_annual_dates(2016, '2024-07-31')

# Patient and practice measures flags to loop
flags = ["patient_measures", "practice_measures"]

# Temple for measures generation, for each combination of patient/practice measure and start_intv date
yaml_template = """
  generate_{flag}_{date}:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/{flag}/{flag}_{date}.csv.gz
      --
      --{flag}
      --start_intv {date}
    outputs:
      highly_sensitive:
        dataset: output/{flag}/{flag}_{date}.csv.gz
"""

yaml_body = ""
needs = {}

# Iterate over flags
for flag in flags:
  needs[flag] = []

  # Iterate over dates and generate yaml list of needs for each combination
  for date in dates:
    yaml_body += yaml_template.format(flag = flag, date = date)
    needs[flag].append(f"generate_{flag}_{date}")

  # Join list into string for each flag
  needs[flag] = ", ".join(needs[flag])

# --- YAML APPT REPORT ---
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
     run: r:latest analysis/appointments/app_processing.r
     needs: [{appt_list}]
     outputs:
       moderately_sensitive:
         table_rounded: output/appointments/app_measures_rounded_*.csv
         table_pivot: output/appointments/app_pivot_table_*.csv
"""
yaml_appt_processing = yaml_appt_processing_template.format(appt_list=appt_list)

yaml_appt_report = yaml_appt_report + yaml_appt_processing

# --- YAML FILE PROCESSING ---
yaml_processing = """
  generate_pre_processing_ungrouped:
    run: python:latest analysis/pre_processing_ungrouped.py
    needs: [{needs_practice}]
    outputs:
      highly_sensitive:
        ungrouped_measures: output/ungrouped_measures/proc_ungrouped_measures*.arrow
  generate_pre_processing_practice:
    run: python:latest analysis/pre_processing_practice.py
    needs: [{needs_practice}]
    outputs:
      highly_sensitive:
        practice_measure: output/practice_measures/proc_practice_measures*.arrow
  generate_pre_processing_patient:
    run: python:latest analysis/pre_processing_patient.py
    needs: [{needs_patient}]
    outputs:
      highly_sensitive:
        patient_measure: output/patient_measures/proc_patient_measures*.arrow
      # moderately_sensitive:
      #   frequency_table: output/patient_measures/frequency_table.csv
  #generate_tables:
  #  run: r:latest analysis/table_generation.r
  #  needs: [generate_pre_processing_practice, generate_pre_processing_patient]
  #  outputs:
  #    moderately_sensitive:
  #      total_measures_tables: output/total_measures/plots/*.csv
  #      practice_measures_tables: output/practice_measures/plots/*.csv
  #      patient_measures_tables: output/patient_measures/plots/*.csv
  #      total_measures_plots: output/total_measures/plots/*.png
  #      practice_measures_plots: output/practice_measures/plots/*.png
  #      patient_measures_plots: output/patient_measures/plots/*.png
"""
yaml_processing = yaml_processing.format(needs_practice = needs["practice_measures"], 
                                         needs_patient = needs["patient_measures"])

# --- YAML TESTING ---
yaml_test = '''
  generate_patient_measures_test:
    run: ehrql:v1 generate-measures analysis/wp_measures.py 
      --output output/patient_measures/patient_measures_2016-08-10_test.csv.gz
      --
      --patient_measures
      --start_intv 2016-08-10
      --test
    outputs:
      highly_sensitive:
        dataset: output/patient_measures/patient_measures_2016-08-10_test.csv.gz
  generate_practice_measures_test:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/practice_measures/practice_measures_2016-08-10_test.csv.gz
      --
      --practice_measures
      --start_intv 2016-08-10
      --test
    outputs:
      highly_sensitive:
        dataset: output/practice_measures/practice_measures_2016-08-10_test.csv.gz
  generate_pre_processing_ungrouped_test:
    run: python:latest analysis/pre_processing_ungrouped.py --test
    needs: [generate_practice_measures_test]
    outputs:
      highly_sensitive:
        ungrouped_measures: output/ungrouped_measures/proc_ungrouped_measures_test.csv.gz
  generate_pre_processing_patient_test:
    run: python:latest analysis/pre_processing_patient.py --test
    needs: [generate_patient_measures_test]
    outputs:
      highly_sensitive:
        patient_measure: output/patient_measures/proc_patient_measures_test.csv.gz
      # moderately_sensitive:
      #   frequency_table: output/patient_measures/frequency_table_test.csv
  generate_pre_processing_practice_test:
    run: python:latest analysis/pre_processing_practice.py --test
    needs: [generate_practice_measures_test]
    outputs:
      highly_sensitive:
        practice_measure: output/practice_measures/proc_practice_measures_test.csv.gz
  #generate_tables_test:
  #  run: r:latest analysis/table_generation.r --test
  #  needs: [generate_pre_processing_practice_test, generate_pre_processing_patient_test]
  #  outputs:
  #    moderately_sensitive:
  #      total_measures_tables_test: output/total_measures/plots/*_test.csv
  #      practice_measures_tables_test: output/practice_measures/plots/*_test.csv
  #      patient_measures_tables_test: output/patient_measures/plots/*_test.csv
  #      total_measures_plots_test: output/total_measures/plots/*_test.png
  #      practice_measures_plots_test: output/practice_measures/plots/*_test.png
  #      patient_measures_plots_test: output/patient_measures/plots/*_test.png
  #generate_test_data:
  #  run: ehrql:v1 generate-dataset analysis/dataset.py --output output/patient_measures/test.csv --test-data-file analysis/test_dataset.py
  #  outputs:
  #    highly_sensitive:
  #      dataset: output/patient_measures/test.csv
'''
# --- Combine scripts and print file ---
yaml = yaml_header + yaml_body + yaml_appt_report + yaml_processing + yaml_test

with open("project.yaml", "w") as file:
       file.write(yaml)