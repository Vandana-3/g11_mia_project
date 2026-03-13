# Granular Column Lineage & Flowchart

This document provides the low-level mapping of every raw data column to its final destination in the ML datasets.

## Detailed Mermaid Code

You can paste this into the [Mermaid Live Editor](https://mermaid.live/) for a high-resolution view.

```mermaid
graph TD
    %% External Authorities
    subgraph "0. External API Sources"
        EXT1["<b>ArcGIS API</b><br/>(Postal → Lat/Long)"]
        EXT2["<b>StatCan Boundary API</b><br/>(Lat/Long → DAUID)"]
    end

    %% Source Definitions
    subgraph "1. Raw Inputs"
        R1["DA_2016.csv<br/>(Census Features)"]
        R2["DA_2021.csv<br/>(Census Features)"]
        R3["mckc_raw.csv<br/>(Clinic Truth)"]
    end

    subgraph "Pre-Process: src/generate_crosswalk.py"
        XW["<b>Crosswalk Engine</b><br/>Resolves Postals to DAUIDs"]
        CW["<b>post_to_dauid.csv</b><br/>(Local Link File)"]
    end

    R3 -- "Extract Postals" --> XW
    EXT1 & EXT2 -- "Spatial Resolution" --> XW
    XW --> CW

    %% Column Level Mapping
    subgraph "2. Mapping & Linking"
        M1["Instability_DA16 / households_dwellings<br/>→ instability"]
        M2["Deprivation_DA16 / material_resources<br/>→ deprivation"]
        M3["Dependency_DA16 / age_labourforce<br/>→ dependency"]
        M4["Ethniccon_DA16 / racialized_NC_pop<br/>→ ethnic_concentration"]
        M5["Subject ID<br/>→ total_volume"]
    end

    R1 --> M1 & M2 & M3 & M4
    R2 --> M1 & M2 & M3 & M4
    R3 --> M5

    %% Process Junctions
    subgraph "3. base_data_builder.py"
        P1["<b>Standardization Engine</b><br/>Cleans DAUIDs<br/>Maps Patients via Crosswalk"]
        BASE["<b>ml_data_long.csv</b><br/>(The Unified Blueprint)"]
    end

    M1 & M2 & M3 & M4 --> P1
    M5 --> P1
    CW --> P1
    P1 --> BASE

    subgraph "4. synthetic_data_generator.py"
        P2B["<b>Interpolation Logic</b><br/>Simulates 2017-2020 Features<br/><i>val_t = val_16 + (t/5) * Δval</i>"]
        
        P2A["<b>Gamma Engine (γ)</b><br/>Learns clinic sensitivity<br/><i>γ = |Slope| / Mean_Volume</i>"]
        
        P3["<b>Simulation Engine</b><br/>Generates History via Backcasting<br/><i>Exp_t = max(0.05, V21 * Impact)</i>"]
    end

    BASE -- "Ingests Blueprint" --> P2B
    P2B -- "Historical OMI Trend" --> P2A
    P2A --> P3

    %% Output Definition
    subgraph "5. Final ML Datasets"
        T1["ml_train_2016.csv<br/>(Hybrid Year)"]
        T2["ml_train_2017-2020.csv<br/>(Synthetic Train)"]
        T3["ml_validation_2021.csv<br/>(Ground Truth)"]
    end

    P2B -- "Real 2016 Pillars" --> T1
    P3 -- "Backcasted Counts" --> T1 & T2
    BASE -- "Observed 2021" --> T3

    %% Styling
    style T3 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style T1 fill:#fff8e1,stroke:#fbc02d,stroke-width:2px
    style BASE fill:#f3e5f5,stroke:#7b1fa2,stroke-dasharray: 5 5
    style P3 fill:#e1f5fe,stroke:#01579b
    style XW fill:#fff3e0,stroke:#ff9800
```

## Transformation Logic Table

| Final Column | Raw Input | Logic Used |
| :--- | :--- | :--- |
| `instability` | `Instability_DA16` (2016) | `val16 + frac * (val21 - val16)` |
| `deprivation` | `Deprivation_DA16` (2016) | `val16 + frac * (val21 - val16)` |
| `dependency` | `Dependency_DA16` (2016) | `val16 + frac * (val21 - val16)` |
| `ethnic_concentration` | `Ethniccon_DA16` (2016) | `val16 + frac * (val21 - val16)` |
| `omi_composite` | Mean(4 pillars) | Calculated *post-interpolation*. |
| `patient_volume` | Real 2021 Patients | **Anchor** for backcasting history. |
| `patient_volume` | 2016-2020 History | `Random_Poisson(Expected_Backcast)` |
