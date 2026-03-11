# Ontario Renal Data Prep (Milestone Data Layer)

## What this project does
This project prepares a DAUID-level dataset for renal-demand forecasting.

Main output:
- `data/processed/ml_base_2021.csv`

It links:
1. ON-Marg features (2016 and 2021)
2. Patient postal-code data
3. Postal-code -> DAUID crosswalk

Then it creates:
- 2021 base table for ML
- synthetic 2016-2020 training set
- 2021 holdout set

## Plain-language terms
- `DAUID`: Small census area ID in Canada.
- `ON-Marg`: Socioeconomic scores for each DAUID.
- `Crosswalk`: A lookup table from postal code to DAUID.
- `Patient volume`: How many patients are assigned to each DAUID.
- `Deprivation coefficient (gamma)`: A number that controls how strongly deprivation changes patient counts in synthetic backcasting.

## Current code layout
- `src/config.py`: paths, patterns, constants
- `src/pipeline.py`: all data functions and orchestration helpers
- `src/main.py`: command-line entry point
- `CODE_FLOW_FOR_BEGINNERS.md`: step-by-step explanation of how functions connect

## Single Colab notebook version
If you want everything in one file for class/demo use, use:
- `notebooks/renal_data_pipeline_all_in_one_colab.ipynb`

This notebook contains the full pipeline with detailed inline documentation and comments.
Use this when you want a single runnable artifact in Google Colab.

## Run command
```bash
cd g11_mia_project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

## What the pipeline does (step by step)
1. Finds ON-Marg 2016 and 2021 files.
2. Cleans and standardizes ON-Marg columns to:
   - `DAUID`
   - `material_deprivation`
   - `residential_instability`
   - `dependency`
   - `ethnic_concentration`
3. Finds patient file (supports MCKC anonymized file names and schema).
4. Cleans patient postals (uppercase, remove spaces/symbols, drop invalid).
5. Finds crosswalk.
   - If missing, builds an **approximate** crosswalk from DA boundaries + postal points (Ontario).
   - If that fails, uses a synthetic fallback (demo only).
6. Maps patients to DAUID.
7. Aggregates to `patient_volume_2021`.
8. Builds 2021 ML base table.
9. Estimates deprivation coefficient by regression (true or demo label).
10. Generates synthetic temporal data:
    - train: 2016-2020
    - holdout: 2021
11. Writes QA reports and assumptions.

## Input discovery
Search order:
1. `data/raw/onmarg/`, `data/raw/crosswalk/`, `data/raw/patients/`
2. `~/Downloads`

## Supported patient files
Examples:
- `MCKC_Gen Neph Postal Codes.xlsx`
- `*patient*.csv/.xlsx`
- `*orn*.csv/.xlsx`

Patient schema detection is automatic. The pipeline looks for a postal-code column and patient-like fields.

## Outputs
### Core outputs
- `data/interim/onmarg_2016_clean.csv`
- `data/interim/onmarg_2021_clean.csv`
- `data/interim/crosswalk_clean.csv`
- `data/interim/patients_clean.csv`
- `data/interim/patient_volume_by_dauid_2021.csv`
- `data/processed/ml_base_2021.csv`

### Synthetic/backcasting outputs
- `data/interim/deprivation_coefficient_estimate.csv`
- `data/interim/synthetic_patient_volume_by_dauid_2016_2021.csv`
- `data/processed/ml_train_synthetic_2016_2020.csv`
- `data/processed/ml_validation_2021_observed.csv`

### QA outputs
- `outputs/qa/schema_summary.md`
- `outputs/qa/qa_report.md`
- `outputs/qa/unmapped_postal_codes.csv`
- `outputs/qa/deprivation_coefficient_report.md`

## Milestone status (what is done vs not done)
### Done
- ON-Marg 2016/2021 cleaning and harmonization
- Postal cleaning and patient preprocessing
- DAUID-level linkage flow and 2021 target aggregation
- Regression-based deprivation coefficient estimation (labeled true/demo)
- Linear interpolation for yearly OMI features (2016->2021)
- Backcasting + Poisson noise for 2016-2020 synthetic training data
- 2021 holdout file creation

### Not fully done yet (why)
- `True` deprivation coefficient is not yet possible in this environment because:
  - crosswalk is **approximate** (DA boundaries + postal points), not official PCCF linkage
  - patient file needed default assumptions (`patient_count=1`, `year=2021`) due missing fields
- Real ORN 2021 ground-truth validation still needs:
  1. official postal->DAUID crosswalk (PCCF or equivalent)
  2. patient file with explicit volume definition for 2021

## Important caution
Current outputs are suitable for course workflow, reproducibility, and model prototyping.
Do not present them as final real-world validated performance until real crosswalk + final 2021 ORN ground-truth labels are used.
