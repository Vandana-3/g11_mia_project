# Milestone Data Status (Team Share)

## Scope covered
- Data linkage path: patient postal -> DAUID -> OMI
- Preprocessing and QA reporting
- Synthetic historical data generation for 2016-2020
- 2021 holdout output creation

## Completed
- OMI 2016/2021 cleaned and harmonized
- Patient file ingestion for anonymized MCKC source
- Crosswalk fallback logic implemented (synthetic, deterministic)
- DAUID-level 2021 target aggregation
- 2021 ML base dataset output
- Deprivation-coefficient regression step implemented
- Synthetic training set + 2021 holdout set generated

## Current limitations
- No official real crosswalk file in environment
- MCKC file required defaults for missing `patient_count` and `year`
- Deprivation coefficient currently labeled `demo`, not `true`

## Required for final true-validation stage
1. Real postal->DAUID crosswalk (StatsCan linkage)
2. Final ORN 2021 patient-volume schema and file
3. Rerun pipeline and confirm coefficient switches to `true`

## Key output files
- `data/processed/ml_base_2021.csv`
- `data/processed/ml_train_synthetic_2016_2020.csv`
- `data/processed/ml_validation_2021_observed.csv`
- `outputs/qa/qa_report.md`
- `outputs/qa/deprivation_coefficient_report.md`
