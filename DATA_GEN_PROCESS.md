# Data Generation Process

This document details how we transform raw census data into long-format ML training sets.

## Mathematical Engine

### 1. Sensitivity Estimation (Gamma)
We analyze the 2021 data to find the relationship between marginalization (OMI) and patient counts.
`Gamma (γ) = |Slope| / Mean_Volume` (Clamped 0.05 - 0.5)

### 2. Backcasting Formula
For years 2016-2020, we calculate the "Expected Volume" based on the anchors of 2021:
`Expected_t = max(0.05, V2021 * (1 - γ * (OMI_2021 - OMI_t)))`

### 3. Stochastic Noise (Poisson)
To prevent model overfitting, integer counts are generated via a Poisson distribution:
`Final_Count = Poisson(Expected_t)`

## Logic Flow

```mermaid
graph LR
    A[Raw Census/Patients] --> B[Standardize & Link]
    B -- "base_data_builder.py" --> C[Interpolate OMI 2017-2020]
    C --> D[Estimate Gamma]
    D --> E[Backcast Volumes]
    E --> F[Yearly CSV Splits]
```

## Data Status Table
| Year | Type | Feature Source | Volume Source |
| :--- | :--- | :--- | :--- |
| **2016** | Hybrid | Observed Census | Synthetic Backcast |
| **2017-2020**| Synthetic | Interpolated | Synthetic Backcast |
| **2021** | Real | Observed Census | Observed Clinic Data |
