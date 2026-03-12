# QA Report

Run timestamp: 2026-03-10T22:47:26
Target year: 2021

## Input Row Counts
- ON-Marg 2016 rows: 20160
- ON-Marg 2021 rows: 20468
- Crosswalk rows (clean): 12162
- Patient rows (clean): 1399

## Mapping Quality
- Mapping rate (rows): 19.44%
- Mapping rate (patient_count): 19.44%
- Unmapped postal codes: 1026

## Final Output
- Final DAUID row count: 20468
- Patient source type: `real`
- Patient source file: `/Users/vandanakala/Downloads/MCKC_Gen Neph Postal Codes.xlsx`

## Crosswalk Mode
- Is synthetic crosswalk: False
- Synthetic strategy: `n/a`

## Deprivation Coefficient
- Coefficient type: `demo`
- Gamma estimate: 0.03026720760903748
- Why not true (if demo): Patient data needed default assumptions (missing patient_count/year).

## Temporal Outputs
- Train file (2016-2020): `/Users/vandanakala/Documents/New project/data/processed/ml_train_synthetic_2016_2020.csv`
- Validation file (2021 holdout): `/Users/vandanakala/Documents/New project/data/processed/ml_validation_2021_observed.csv`
- Train rows: 98590
- Validation rows: 19718

## Warnings
- Deprivation coefficient is demo-only because true-data conditions are not fully met.

## Blockers
- None

## Assumptions Applied
- patient_count column missing; defaulted each row to 1
- year column missing; defaulted all rows to 2021