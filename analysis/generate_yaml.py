# TODO:
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
from parse_args import config

dates = generate_annual_dates(config["study_end_date"], config["n_years"])

# --- YAML HEADER ---

yaml_header = """
version: '3.0'

expectations:
  population_size: 1000

actions:
"""

# ------- YAML MEASURES --------------------------------------------

# Patient and practice measures flags to loop
flags = ["practice_measures"]
# Set of measures to loop
measure_sets = ["all", "sro", "resp"]
# Appt variants
appt_variants = ["", "_appt"]
# Yearly variant
yearly_variant = ["", "_yearly"]

# Temple for measures generation, for each combination of patient/practice measure and start_intv date
yaml_measures_template = """
  generate_{flag}_{set}_{date}{appt_suffix}{yearly_suffix}:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/{flag}_{set}{appt_suffix}/{flag}_{date}{yearly_suffix}.arrow
      --
      --{flag}
      --start_intv {date}
      --set {set}{appt_flag}{yearly_flag}
      
    outputs:
      highly_sensitive:
        dataset: output/{flag}_{set}{appt_suffix}/{flag}_{date}{yearly_suffix}.arrow
"""

yaml_measures = ""
needs = {}

# Iterate over flags
for flag in flags:

    # Iterate over sets of measures
    for set in measure_sets:

        # Iterate over appt variants
        for appt_suffix, appt_flag in zip(appt_variants, ["", " --appt"]):
            
            for yearly_suffix, yearly_flag in zip(yearly_variant, ["", " --yearly"]):

              needs[f"{flag}_{set}{appt_suffix}{yearly_suffix}"] = []

              # Iterate over dates and generate yaml list of needs for each combination
              for date in dates:

                  yaml_measures += yaml_measures_template.format(
                      flag=flag,
                      date=date,
                      set=set,
                      appt_suffix=appt_suffix,
                      appt_flag=appt_flag,
                      yearly_suffix=yearly_suffix,
                      yearly_flag=yearly_flag,
                  )
                  needs[f"{flag}_{set}{appt_suffix}{yearly_suffix}"].append(
                      f"generate_{flag}_{set}_{date}{appt_suffix}{yearly_suffix}"
                  )

              # Join list into string for each flag
              needs[f"{flag}_{set}{appt_suffix}{yearly_suffix}"] = ", ".join(
                  needs[f"{flag}_{set}{appt_suffix}{yearly_suffix}"]
              )

yaml_measures_test_template = """
# --------------- TEST ACTIONS ------------------------------------------

  # generate_demograph_measures_{set}{appt_suffix}_test:
  #   run: ehrql:v1 generate-measures analysis/wp_measures.py 
  #     --output output/demograph_measures_{set}{appt_suffix}/demograph_measures_{start_date}_test.arrow
  #     --
  #     --demograph_measures
  #     --start_intv {start_date}
  #     --test
  #     --set {set}{appt_flag}
  #   outputs:
  #     highly_sensitive:
  #       dataset: output/demograph_measures_{set}{appt_suffix}/demograph_measures_{start_date}_test.arrow
  generate_practice_measures_{set}{appt_suffix}{yearly_suffix}_test:
    run: ehrql:v1 generate-measures analysis/wp_measures.py
      --output output/practice_measures_{set}{appt_suffix}{yearly_suffix}/practice_measures_{start_date}_test.arrow
      --
      --practice_measures
      --start_intv {start_date}
      --test
      --set {set}{appt_flag}{yearly_flag}
    outputs:
      highly_sensitive:
        dataset: output/practice_measures_{set}{appt_suffix}{yearly_suffix}/practice_measures_{start_date}_test.arrow
  # generate_comorbid_measures_{set}{appt_suffix}_test:
  #   run: ehrql:v1 generate-measures analysis/wp_measures.py
  #     --output output/comorbid_measures_{set}{appt_suffix}/comorbid_measures_{start_date}_test.arrow
  #     --
  #     --comorbid_measures
  #     --start_intv {start_date}
  #     --test
  #     --set {set}{appt_flag}
  #   outputs:
  #     highly_sensitive:
  #       dataset: output/comorbid_measures_{set}{appt_suffix}/comorbid_measures_{start_date}_test.arrow
"""
yaml_measures_test = ""
for set in measure_sets:
    for appt_suffix, appt_flag in zip(appt_variants, ["", " --appt"]):
        for yearly_suffix, yearly_flag in zip(yearly_variant, ["", " --yearly"]):
          yaml_measures_test += yaml_measures_test_template.format(
              start_date=config["test_config"]["start_date"],
              set=set,
              appt_suffix=appt_suffix,
              appt_flag=appt_flag,
              yearly_suffix=yearly_suffix,
              yearly_flag=yearly_flag,
          )

# --------------- YAML APPT REPORT ------------------------------------------
yaml_appt_report = ""

appt_dates = {
    1: datetime.strptime("2023-07-01", "%Y-%m-%d").date(),
    2: datetime.strptime("2023-12-01", "%Y-%m-%d").date(),
    3: datetime.strptime("2018-07-01", "%Y-%m-%d").date(),
    4: datetime.strptime("2018-12-01", "%Y-%m-%d").date(),
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
    yaml_appt_report += yaml_appt_template.format(key=key, appt_date=value)
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
yaml_appt_report += (
    " \n # --------------- PROCESSING ------------------------------------------\n"
)

groups = []
for flag in flags:
    groups.append(flag.replace("_measures", "")) # practice/demograph/comorbid

yaml_processing_template = """
  generate_freq_table_{group}_{set}{appt_suffix}{test_suffix}:
    run: python:v2 analysis/freq_table.py --{group}_measures --set {set}{appt_flag}{test_flag}
    needs: [{needs}{test_suffix}]
    outputs:
      moderately_sensitive:
        freq_table: output/{group}_measures_{set}{appt_suffix}/freq_table_{group}{test_suffix}.csv
  generate_pre_processing_{group}_{set}{appt_suffix}{test_suffix}:
    run: python:v2 analysis/pre_processing.py --{group}_measures --set {set}{appt_flag}{test_flag}
    needs: [{needs}{test_suffix}]
    outputs:
      highly_sensitive:
        measures: output/{group}_measures_{set}{appt_suffix}/proc_{group}_measures{test_suffix}.arrow
  generate_rounding_{group}_{set}{appt_suffix}{test_suffix}:
    run: r:v2 analysis/round_measures.r --{group}_measures --set {set}{appt_flag}{test_flag}
    needs: [generate_pre_processing_{group}_{set}{appt_suffix}{test_suffix}]
    outputs:
      highly_sensitive:
        rounded_measures: output/{group}_measures_{set}{appt_suffix}/proc_{group}_measures_midpoint6{test_suffix}.arrow
  generate_normalization_{group}_{set}{appt_suffix}{test_suffix}:
    run: python:v2 analysis/normalization.py --{group}_measures --set {set}{appt_flag}{test_flag}
    needs: [generate_rounding_{group}_{set}{appt_suffix}{test_suffix}]
    outputs:
      highly_sensitive:
        practice_level_tables: output/{group}_measures_{set}{appt_suffix}/practice_level_counts{test_suffix}.arrow
      moderately_sensitive:
        seasonal_tables_tables: output/{group}_measures_{set}{appt_suffix}/Results*{test_suffix}.csv
"""

yaml_processing = ""
yaml_processing_test = ""
for group in groups:
    for set in measure_sets:
        for appt_suffix, appt_flag in zip(appt_variants, ["", " --appt"]):
            # Actions for processing real data
            yaml_processing += yaml_processing_template.format(
                group=group,
                needs=needs[f"{group}_measures_{set}{appt_suffix}"],
                test_suffix="",
                test_flag="",
                set=set,
                appt_suffix=appt_suffix,
                appt_flag=appt_flag,
            )

for group in groups:
    for set in measure_sets:
        for appt_suffix, appt_flag in zip(appt_variants, ["", " --appt"]):
            # Actions for processing test data
            yaml_processing_test += yaml_processing_template.format(
                group=group,
                needs=f"generate_{group}_measures_{set}{appt_suffix}",
                test_suffix="_test",
                test_flag=" --test",
                set=set,
                appt_suffix=appt_suffix,
                appt_flag=appt_flag,
            )

yaml_viz = " \n # --------------- VISUALIZATION ACTIONS ------------------------------------------"

yaml_viz_template = """

  generate_deciles_charts_{set}{appt_suffix}{test_suffix}:
    run: >
      r:v2 analysis/decile_charts.r {test_flag} --set {set}{appt_flag}
    needs: [generate_rounding_practice_{set}{appt_suffix}{test_suffix}] 
    outputs:
      moderately_sensitive:
        deciles_charts: output/practice_measures_{set}{appt_suffix}/plots{test_suffix}/decile_chart_*_rate_mp6.png
        deciles_table: output/practice_measures_{set}{appt_suffix}/decile_tables/decile_table_*_rate_mp6{test_suffix}.csv
  
  generate_decomposition_plots_{set}{appt_suffix}{test_suffix}:
    run: >
      r:v2 analysis/decomposition.r {test_flag} --set {set}{appt_flag}
    needs: [generate_rounding_practice_{set}{appt_suffix}{test_suffix}]
    outputs:
      moderately_sensitive:
        decomposition_plots: output/practice_measures_{set}{appt_suffix}/decompositions/*{test_suffix}.png
        decomposition_summaries: output/practice_measures_{set}{appt_suffix}/decompositions/summary_*{test_suffix}.txt
"""

""" TEMPORARILY COMMENTED OUT:

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

  generate_deciles_charts_RR{test_suffix}:
    run: >
      r:v2 analysis/decile_charts.r --RR {test_flag}
    needs: [generate_normalization{test_suffix}]
    outputs:
      moderately_sensitive:
        deciles_charts: output/practice_measures/plots/decile_chart_*_RR{test_suffix}.png
        deciles_table: output/practice_measures/decile_tables/decile_table_*_RR{test_suffix}.csv
"""

suffixes = ["", "_test"]
test_flags = ["", "--test"]
for test_suffix, test_flag in zip(suffixes, test_flags):
    for set in measure_sets:
        for appt_suffix, appt_flag in zip(appt_variants, ["", " --appt"]):
            yaml_viz += yaml_viz_template.format(
                test_suffix=test_suffix,
                test_flag=test_flag,
                set=set,
                appt_suffix=appt_suffix,
                appt_flag=appt_flag,
            )

yaml_sense_check = " \n # --------------- SENSE CHECK ACTIONS ------------------------------------------"

yaml_sense_check_template = """

  generate_sense_check_{set}{appt_suffix}:
    run: python:v2 analysis/sense_check.py --test --practice_measures --set {set}{appt_flag}
    needs: [generate_practice_measures_{set}{appt_suffix}_test]
    outputs:
      moderately_sensitive:
        totals: output/practice_measures_{set}{appt_suffix}/sense_check*.csv
"""

for set in measure_sets:
    for appt_suffix, appt_flag in zip(appt_variants, ["", " --appt"]):
          yaml_sense_check += yaml_sense_check_template.format(
              set=set,
              appt_suffix=appt_suffix,
              appt_flag=appt_flag,
            )

yaml_other = """

  # --------------- OTHER ACTIONS ------------------------------------------

  # Assurance test
  generate_dataset:
    run: >
        ehrql:v1 generate-dataset
        analysis/dataset.py
        --test-data-file analysis/test_dataset.py
        --output output/dataset.csv
    outputs:
      highly_sensitive:
        population: output/dataset.csv  
"""

yaml_yearly = " \n # --------------- VISUALIZATION ACTIONS ------------------------------------------"

needs_list = []
for date in dates:
    needs_list.append(f"generate_practice_measures_resp_{date}_yearly")

yaml_yearly_template = """
    # Yearly pipeline
  generate_pre_processing_practice_resp_yearly{test_suffix}:
    run: python:v2 analysis/pre_processing.py --practice_measures --set resp --yearly {test_flag}
    needs: [{needs_str}]
    outputs:
      highly_sensitive:
        measures: output/practice_measures_resp_yearly/proc_practice_measures{test_suffix}.arrow
  generate_rounding_practice_resp_yearly{test_suffix}:
    run: r:v2 analysis/round_measures.r --practice_measures --set resp --yearly {test_flag}
    needs: [generate_pre_processing_practice_resp_yearly{test_suffix}]
    outputs:
      highly_sensitive:
        rounded_measures: output/practice_measures_resp_yearly/proc_practice_measures_midpoint6{test_suffix}.arrow
  generate_deciles_charts_resp_yearly{test_suffix}:
    run: >
      r:v2 analysis/decile_charts.r --set resp --yearly {test_flag}
    needs: [generate_rounding_practice_resp_yearly{test_suffix}] 
    outputs:
      moderately_sensitive:
        deciles_charts: output/practice_measures_resp_yearly/plots{test_suffix}/decile_chart_*_rate_mp6.png
        deciles_table: output/practice_measures_resp_yearly/decile_tables/decile_table_*_rate_mp6{test_suffix}.csv
  generate_bar_plot_yearly{test_suffix}:
    run: >
      r:v2 analysis/yearly_measures_analysis.r --set resp --yearly {test_flag}
    needs: [generate_rounding_practice_resp_yearly{test_suffix}] 
    outputs:
      moderately_sensitive:
        bar_plot: output/practice_measures_resp_yearly/zero_rate_practices{test_suffix}.png
"""

for test_suffix, test_flag in zip(suffixes, test_flags):
    if test_suffix == "_test":
        needs_str = "generate_practice_measures_resp_yearly_test"
    else:
        needs_str = ", ".join(needs_list)
    yaml_yearly += yaml_yearly_template.format(
        needs_str=needs_str,
        test_suffix=test_suffix,
        test_flag=test_flag,
    )

# -------- Combine scripts and print file -----------

yaml = (
    yaml_header
    + yaml_measures
    + yaml_appt_report
    + yaml_processing
    + yaml_viz
    + yaml_measures_test
    + yaml_processing_test
    + yaml_sense_check
    + yaml_other
    + yaml_yearly
)

with open("/workspaces/winter-pressures-phase-II/project.yaml", "w") as file:
    file.write(yaml)
