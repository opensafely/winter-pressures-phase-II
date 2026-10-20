# winter-pressures-phase-II

## Pipeline Overview

This project contains three OpenSAFELY pipelines for generating and analysing measures of pressure.  
Each pipeline stratifies measures by different characteristics and includes support for testing and configuration.

## Setup

There are two main pipelines:
1. **Practice-level measures** - Extracts all measures described in original protocol
2. **Patient-level subgroup measures** - Extracts only good-candidate measures (determined as those with high usage across practices and potential seasonality)

Note - Prior versions had dedicated national **demographic** and **comorbidity** pipelines containing intersectional subgroups e.g. age X sex. These were removed as practice-level univariate subgroup breakdowns were deemed to be more useful for pressure management than national level multivariate breakdowns.

To choose which pipeline to run, add the corresponding flag when calling the script:
- `--practice_measures`
- `--practice_subgroup_measures`

### Test mode
Use the `--test` flag with any script to run the lightweight test pipeline (useful in Codespaces, since the default dummy data is sparse).

### Measure sets
There are currently three sets of measures:
- `--set appts_table` - runs appts_table measures  
- `--set sro` - runs sro measures (+ secondary referral measures)
- `--set resp` - runs respiratory illness measures (rsv/flu/covid)

### Helper scripts and configuration
- **Configuration**
  - `config.json` and `wp_config_setup.py`: pipeline flags, dates, filetypes, and parameters  
  - `codelist_definition.py`: defines codelists  
- **Testing**
  1. Measure definitions copied to `dataset.py`. Note - this requires manual copying, the definitions in `dataset.py` can lag behind the cuurent definitions in `measures_definition.py`.
  2. Dummy test data defined in `test_dataset.py`
  3. ehrQL assurance test then run on `dataset.py`
- **Utilities**
  - Helper functions: `utils.r` and `utils.py`
- **Action generation**
  - `generate_yaml.py` automatically creates the GitHub Actions YAML workflow

## Running the pipeline

1. **Generate measures**
   - Measures are split by year.
   - Example:  
     ```bash
     opensafely run generate_practice_measures_2016-04-11
     ```
     This runs `wp_measures.py`.  
   - Specific measure queries are defined in `queries.py`.

2. **OUT OF DATE - Generate frequency table (Table 1)**
   - Available only for the demographics pipeline.
   - Example:  
     ```bash
     opensafely run generate_freq_table_demograph
     ```
     Runs `freq_table.py`.

3. **Pre-process and round measures into a single file**
   - Example:  
     ```bash
     opensafely run generate_pre_processing_practice
     ```
     Runs `pre_processing.py`.

   - From rounded measures, you can generate decile tables and charts for local visualisation:
     - `opensafely run generate_deciles_charts` → `decile_charts.r`
     - For subgroup pipelines, line plots are generated via `table_generation.r` *(action not yet available)*

5. **Generate practice-level seasonal rates**
   - Example:  
     ```bash
     opensafely run generate_normalization_practice
     ```
     Runs `normalization.py`.

6. **Conduct statistical analysis and calculate rate ratios**
   - Runs `stat_test.r`.

## Notes
- The pipeline is modular: you can rerun individual steps as needed.
- Test mode (`--test`) is intended for development environments, not production runs.


[View on OpenSAFELY](https://jobs.opensafely.org/repo/https%253A%252F%252Fgithub.com%252Fopensafely%252Fwinter-pressures-phase-II)

Details of the purpose and any published outputs from this project can be found at the link above.

The contents of this repository MUST NOT be considered an accurate or valid representation of the study or its purpose. 
This repository may reflect an incomplete or incorrect analysis with no further ongoing work.
The content has ONLY been made public to support the OpenSAFELY [open science and transparency principles](https://www.opensafely.org/about/#contributing-to-best-practice-around-open-science) and to support the sharing of re-usable code for other subsequent users.
No clinical, policy or safety conclusions must be drawn from the contents of this repository.

# About the OpenSAFELY framework

The OpenSAFELY framework is a Trusted Research Environment (TRE) for electronic
health records research in the NHS, with a focus on public accountability and
research quality.

Read more at [OpenSAFELY.org](https://opensafely.org).

# Licences
As standard, research projects have a MIT license. 
