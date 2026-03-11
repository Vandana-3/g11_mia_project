# Data Prep Flow (Handover)

This is the step‑by‑step flow of what was executed to prepare the ML‑ready datasets.

## Flow Summary
1. **Inputs loaded**
   ON‑Marg 2016/2021, patient postal codes, DA boundaries (LDA), and postal points (Ontario).
2. **ON‑Marg cleaning**
   DAUID + four OMI dimensions are normalized and saved as clean interim files.
3. **Crosswalk creation (approximate)**
   Postal points are spatially joined to DA polygons to build a postal_code → DAUID crosswalk.
   A nearest‑DA fallback is used for unmatched points.
4. **Patient linkage**
   Patient postals are standardized, linked to DAUID, and aggregated to DAUID for 2021.
5. **ML base table**
   ON‑Marg 2021 features are merged with patient_volume_2021.
6. **Synthetic history (2016–2020)**
   OMI is interpolated, a deprivation coefficient is estimated, and Poisson noise is added to backcast volumes.
7. **QA outputs**
   Schema, QA, and coefficient reports are produced to document assumptions and blockers.

## Key Files Produced
- ML base: `data/processed/ml_base_2021.csv`
- Synthetic training: `data/processed/ml_train_synthetic_2016_2020.csv`
- Holdout validation: `data/processed/ml_validation_2021_observed.csv`
- Crosswalk (approx): `data/raw/crosswalk/crosswalk_approx_from_boundary_points.csv`
- QA reports: `outputs/qa/qa_report.md`, `outputs/qa/schema_summary.md`, `outputs/qa/deprivation_coefficient_report.md`
- Map validation: `outputs/qa/ontario_da_postal_map.html`

## Notes
- The crosswalk is **approximate** (DA boundaries + postal points); it is not PCCF.
- The synthetic data is **demo‑quality** until real ORN patient data and PCCF are available.
