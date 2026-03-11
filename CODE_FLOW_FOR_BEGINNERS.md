# Code Flow For Beginners

This file explains how the code is connected, in plain language.

## Main files
- `src/main.py`: tiny launcher file.
- `src/pipeline.py`: all pipeline logic.
- `src/config.py`: settings and folder paths.

## How execution starts
1. You run: `python -m src.main`
2. `src/main.py` calls `run_pipeline()` from `src/pipeline.py`.
3. `run_pipeline()` runs all steps in order and returns:
   - `context` (everything collected during run)
   - exit code (`0` success, `1` if blockers)

## Pipeline step order inside `run_pipeline()`
1. Create patient template/placeholder files if missing.
2. Discover and clean ON-Marg 2016 + 2021.
3. Discover and clean patient file.
4. Discover crosswalk:
   - use real if available
   - otherwise create synthetic fallback crosswalk
5. Map patients to DAUID and aggregate 2021 patient volume.
6. Build final 2021 ML base table.
7. Estimate deprivation coefficient (true or demo).
8. Generate synthetic temporal data:
   - train: 2016-2020
   - holdout: 2021
9. Write QA and schema reports.

## Why `context` exists
`context` is a dictionary that stores everything important from each step:
- file paths used
- row counts
- warnings/blockers
- output paths

This lets reports be generated without rerunning earlier steps.

## Key output files
- `data/processed/ml_base_2021.csv`
- `data/processed/ml_train_synthetic_2016_2020.csv`
- `data/processed/ml_validation_2021_observed.csv`
- `outputs/qa/qa_report.md`

## Demo vs true logic
The coefficient is marked `demo` when final validation conditions are not met (for example synthetic crosswalk or missing patient columns).
This is intentional for honest reporting in course milestones.
