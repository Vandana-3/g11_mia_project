# Flow Summary (Crisp)

## What is real vs synthetic
- **Real:** ON‑Marg 2016/2021 OMI scores (DAUID level), StatsCan DA boundary polygons (LDA 2016/2021).
- **Approximate (not official PCCF):** Postal→DAUID crosswalk built from DA boundaries + postal points.
- **Synthetic:** Patient counts for 2016–2020; 2021 counts are demo if real ORN file missing.

## End‑to‑end flow to training set
1. **Load ON‑Marg 2016/2021** → clean DAUID + four OMI dimensions.
2. **Load patient data** → clean postal codes and counts.
3. **Crosswalk creation**:
   - Use real crosswalk if provided.
   - Else build **approximate** crosswalk via spatial join (DA polygons + postal points).
   - Else fallback to synthetic crosswalk.
4. **Link patients to DAUID** → aggregate `patient_volume_2021`.
5. **Build ML base** → merge 2021 OMI features + 2021 patient volume.
6. **Estimate deprivation coefficient (gamma)** via regression of OMI vs volume (2021).
7. **Interpolate OMI (2016–2021)** and **backcast counts** for 2016–2020.
8. **Add Poisson noise** to backcasted counts.
9. **Save outputs**:
   - `ml_train_synthetic_2016_2020.csv` (training)
   - `ml_validation_2021_observed.csv` (holdout)
   - `ml_base_2021.csv` (features + target)

## Important notes
- Crosswalk is **approximate** unless PCCF is used.
- Deprivation coefficient is **demo‑only** when inputs are not official.
