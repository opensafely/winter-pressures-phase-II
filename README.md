# winter-pressures-phase-II

## Setup

- There are three pipelines, each stratifying the measures by different characteristics:
  1. Practice
  2. Patient demographic variables
  3. Patient comorbidities.
- To choose which pipeline to run, the appropriate flag should be added to the script call. These are `--practice_measures`, `--demograph_measures`, `--comorbid_measures` respectively.
- Use `--test` flag with any script to run the test pipeline instead. This is used to run a lightweight version in codespaces (because the default dummy data is too sparse).
- Helper scripts
   - Flags, dates, filetypes etc are configurable in `config.r` and `wp_config_setup.py`
   - Codelists configured in `codelist_definition.py`
   - Measures are tested by copying measure definitions to `dataset.py` and specifying test dummy data using `test_dataset.py`
   - Helper functions: `utils.r` and `utils.py`
   - Automatically generate the yaml actions file using `generate_yaml.py`
1. Generate measures
   - Measures are split by year
   - `opensafely run generate_practice_measures_2016-04-11` runs `wp_measures.py`
   - Specific queries used for each measure stored in `queries.py`
2. Generate frequency table (table 1)
   - Only available via demographics pipeline
   - `opensafely run generate_freq_table_demograph` runs `freq_table.py`
4. Pre-process measures into a single process measures file
   - `opensafely run generate_pre_processing_practice` runs `pre_processing.py`
5. Round & redact measures
   - `opensafely run generate_rounding_practice` runs `round_measures.r`
   - From these rounded measures, decile tables can be generated and released for local visualisation:
      - `opensafely run generate_deciles_charts` runs `decile_charts.r`
      - For the demographic and comorbidity pipelines, line plots are generated instead via `table_generation.r` (action not yet available)
6. Generate practice-level rates per season
   - `opensafely run generate_normalization_practice` runs `normalization.py`
7. Conduct statistical analysis and generate rate ratios
   - `stat_test.r`

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
