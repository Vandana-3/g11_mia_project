# Renal Data Project: Synthetic Patient Data Engine

A streamlined pipeline for generating synthetic historical patient datasets in Ontario, anchored by real 2021 observations and socio-economic indicators (ON-Marg).

## Quick Start
1. **Setup Env**: `conda activate mia_project`
2. **Step 1: Link Data**: `python src/base_data_builder.py`
3. **Step 2: Generate History**: `python src/synthetic_data_generator.py`

## Project Structure
- `src/`: Core Python logic.
  - `config.py`: Central path and constant management.
  - `base_data_builder.py`: Links census/patient data into the OMI base.
  - `synthetic_data_generator.py`: Backcasts history 2016-2020.
  - `generate_crosswalk.py`: Geocoding tool for postal mapping.
- `data/`:
  - `raw/`: Source census (ON-Marg) and clinic (mckc_raw) data.
  - `processed/`: Final ML-ready training and validation CSVs.

## Essential Documentation
- [DATA_GEN_PROCESS.md](./DATA_GEN_PROCESS.md): Logic flow and mathematical formulas.
- [TECHNICAL_RATIONALE.md](./TECHNICAL_RATIONALE.md): Scientific justification for Gamma, Poisson, and Backcasting.
- [PIPELINE_HANDOVER.md](./PIPELINE_HANDOVER.md): Operational guide for developers.
- [WHAT_IT_DID.md](./WHAT_IT_DID.md): Transformation summary from legacy to lean.
