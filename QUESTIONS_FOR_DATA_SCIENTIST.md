# Questions for Data Scientist Coordination

This document outlines technical considerations for the machine learning team regarding the generated synthetic datasets.

## 1. Schema Overview
All datasets (`ml_train_2016-2020.csv`, `ml_validation_2021.csv`) follow this structure:
- **`DAUID`**: Geographic index.
- **`year`**: Temporal index.
- **`instability`, `deprivation`, `dependency`, `ethnic_concentration`**: ON-Marg pillars (Features).
- **`omi_composite`**: Mean of pillars (Primary feature).
- **`patient_volume`**: Target variable (Integer counts).
- **`source`**: Data origin (`synthetic` vs `observed`).

## 2. Key Technical Questions

### A. Modeling Assumptions
1. **Sensitivity Coefficient (Gamma)**:
   - We estimated a Gamma of **0.1151** from the 2021 regression. 
   - *Question*: Does this coefficient align with your clinical domain knowledge for this specific patient population?

2. **Wait Time/Lag**:
   - The current model assumes a same-year relationship between OMI and volume.
   - *Question*: Do you expect a "lag" effect (e.g., this year's marginalization impacts next year's patient volume)?

3. **Feature Scaling**:
   - The pillars are currently raw scores (centered around zero).
   - *Question*: Would you like us to apply Min-Max or Standard Scaling before export, or will you handle this in your `DataLoader`?

### B. Statistical Distribution
4. **Zero-Inflation**:
   - Roughly 90% of Ontario DAs have a volume of 0.
   - *Question*: How do you plan to handle zero-inflation (e.g., Tweedie loss, Zero-Inflated Poisson)? Should we provide a balanced sub-sample?

5. **Poisson Variance**:
   - We used the standard `np.random.poisson(expected)`.
   - *Question*: Do you require over-dispersion (Negative Binomial) or more complex stochastic noise to simulate environmental shocks?

### C. Validation Strategy
6. **2021 Holdout**:
   - We designated 2021 as the exclusive validation set because it is the only 100% "Observed" year for both features and volume.
   - *Question*: Is this "Future-Holdout" approach sufficient for your cross-validation strategy?

## 3. Data Pattern Warning
Note that **2016** is a **Hybrid** year. The socio-economic features are strictly observed census data, but the `patient_volume` is synthetic (backcasted) because raw clinic data for 2016 was unavailable.
