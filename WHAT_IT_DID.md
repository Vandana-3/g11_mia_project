# WHAT_IT_DID

This document explains, in plain language, exactly what was done for your Data milestone tasks, what was delivered, and what is still pending.

## A) Goal of your Data milestone (in simple words)
You needed to build the data pipeline that does three things:
1. Link patient postal codes to DAUID
2. Attach ON-Marg deprivation features
3. Create synthetic historical data (2016-2020) while keeping 2021 as holdout

## B) What was done (chronological)

### 1) ON-Marg data setup (2016 and 2021)
- Loaded ON-Marg files from available sources.
- Found DA-level sheets (`DA_2016`, `DA_2021`).
- Standardized columns into one consistent schema:
  - `DAUID`
  - `material_deprivation`
  - `residential_instability`
  - `dependency`
  - `ethnic_concentration`
- Saved cleaned files:
  - `data/interim/onmarg_2016_clean.csv`
  - `data/interim/onmarg_2021_clean.csv`

Why this was done:
- The two ON-Marg files use different original names. Standardizing them is required before joining and modeling.

### 2) Patient file handling
- Added robust patient-file discovery (including MCKC anonymized naming patterns).
- Added schema checks so random unrelated files are ignored.
- Loaded your anonymized file: `MCKC_Gen Neph Postal Codes.xlsx`.
- Cleaned postal codes (uppercase, remove spaces/symbols, drop invalid).

Assumptions applied because of missing columns in MCKC file:
- `patient_count` missing -> defaulted to `1` per row
- `year` missing -> defaulted to `2021`

Why this was done:
- Your file is real anonymized operational data, but it does not provide direct `patient_count` and `year` columns needed by the pipeline schema.

### 3) Crosswalk linkage
- Tried to find real postal->DAUID crosswalk.
- Real crosswalk was not available.
- Implemented synthetic workaround:
  - Builds synthetic crosswalk from observed patient postal codes (deterministic hash assignment to DAUID)
  - Rebuilds stale synthetic crosswalks to match current patient file
- Saved synthetic crosswalk:
  - `data/raw/crosswalk/crosswalk_synthetic_pc_to_dauid.csv`

Why this was done:
- You needed a working linkage pipeline for milestone progress.
- Without any crosswalk, no DAUID-level target can be built.

### 4) DAUID target creation (2021)
- Mapped cleaned patient postals to DAUID.
- Aggregated to `patient_volume_2021`.
- Built final 2021 base file:
  - `data/processed/ml_base_2021.csv`

Why this was done:
- This is the core output needed for forecasting module input.

### 5) Deprivation-coefficient regression step (implemented)
- Added regression step to estimate coefficient from:
  - 2021 OMI composite score
  - current 2021 DAUID patient volume
- Wrote estimate to:
  - `data/interim/deprivation_coefficient_estimate.csv`
- Added human-readable report:
  - `outputs/qa/deprivation_coefficient_report.md`

What label is used:
- `coefficient_type = demo` or `true`

Current run status:
- Coefficient is marked `demo`.

Why marked demo (not true):
- Crosswalk is synthetic (not official geography linkage)
- Patient dataset required default assumptions (`patient_count`, `year`)

### 6) Synthetic historical data generation (implemented)
- Interpolated yearly OMI features from 2016 to 2021 (linear interpolation).
- Backcasted patient volume for 2016-2020.
- Injected Poisson noise into backcast years.
- Kept 2021 as holdout row set (observed from current source pipeline).

Generated files:
- `data/interim/synthetic_patient_volume_by_dauid_2016_2021.csv`
- `data/processed/ml_train_synthetic_2016_2020.csv`
- `data/processed/ml_validation_2021_observed.csv`

Why this was done:
- Your milestone requires synthetic historical generation because ON-Marg only has census snapshots at 2016 and 2021.

### 7) QA and traceability
Generated/updated:
- `outputs/qa/schema_summary.md`
- `outputs/qa/qa_report.md`
- `outputs/qa/unmapped_postal_codes.csv`
- `outputs/qa/deprivation_coefficient_report.md`

What these reports explain:
- exactly which files were used
- what columns were detected
- mapping quality
- assumptions made
- whether coefficient is `true` or `demo`
- what is still blocking final true-validation setup

## C) What was NOT fully done yet (and why)

### Not fully done: true ORN-grade linkage
Reason:
- No official StatsCan crosswalk was available in this environment.
- Synthetic crosswalk is a workaround for coursework progress, not final validation-grade geography.

### Not fully done: true final coefficient per plan
Reason:
- Coefficient can be computed now (done), but it is `demo` quality due to linkage/assumption limits.
- A true final coefficient requires:
  1. real postal->DAUID crosswalk
  2. real ORN 2021 patient volume definition in final schema

## D) Deliverables produced

### Main dataset outputs
- `data/processed/ml_base_2021.csv`
- `data/processed/ml_train_synthetic_2016_2020.csv`
- `data/processed/ml_validation_2021_observed.csv`

### Key interim outputs
- `data/interim/onmarg_2016_clean.csv`
- `data/interim/onmarg_2021_clean.csv`
- `data/interim/patients_clean.csv`
- `data/interim/patient_volume_by_dauid_2021.csv`
- `data/interim/deprivation_coefficient_estimate.csv`
- `data/interim/synthetic_patient_volume_by_dauid_2016_2021.csv`

### QA/report outputs
- `outputs/qa/qa_report.md`
- `outputs/qa/schema_summary.md`
- `outputs/qa/deprivation_coefficient_report.md`
- `outputs/qa/unmapped_postal_codes.csv`

## E) Current interpretation for team communication
- Pipeline is complete and reproducible for milestone data workflow.
- Synthetic-history generation and coefficient step are implemented.
- Current coefficient is demo-labeled (not final) due to missing official crosswalk and missing explicit volume/year fields in patient input.
- Final real-world validation should wait for official crosswalk + final ORN 2021 volume file.
