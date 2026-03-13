# Pipeline Handover Guide

## Prerequisites
- Python 3.9+ 
- Conda Environment: `mia_project`
- Dependencies: `pandas`, `numpy`, `requests`

## Running the Engine

### Full Refresh Sequence
1. **Check Raw Data**: Ensure `data/raw/onmarg/` and `data/raw/patients/mckc_raw.csv` exist.
2. **Regenerate Crosswalk** (Optional): 
   `python src/generate_crosswalk.py`
3. **Consolidate Base**:
   `python src/base_data_builder.py`
4. **Export ML Sets**:
   `python src/synthetic_data_generator.py`

## Troubleshooting
- **Path Issues**: Check `src/config.py` - all paths are relative to `PROJECT_ROOT`.
- **Missing DAUIDs**: If `ml_data_long.csv` looks empty, check `processed/postal_to_dauid_crosswalk.csv` to ensure patients mapped correctly.
- **Gamma Quality**: If synthetic volumes are all zero, check the OMI correlation in `synthetic_data_generator.py`.
