import pandas as pd
import numpy as np
import pathlib
import re

def normalize_dauid(value):
    if pd.isna(value): return None
    text = str(value).strip()
    if text.endswith(".0"): text = text[:-2]
    digits = re.sub(r"\D", "", text)
    return digits if digits else None

# Add project root to path to allow imports if needed
import sys
project_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.config import (
    PROCESSED_DIR,
    ML_DATA_LONG_PATH
)

def main():
    # Paths (from config)
    data_long_path = ML_DATA_LONG_PATH
    processed_dir = PROCESSED_DIR
    
    print("Loading long-format base data...")
    df = pd.read_csv(data_long_path)
    
    # Ensure Ontario Only (DAUID starts with 35)
    df = df[df["DAUID"].astype(str).str.startswith("35")].copy()
    
    # 1. Feature Engineering: OMI Composite
    pillars = ["instability", "deprivation", "dependency", "ethnic_concentration"]
    df["omi_composite"] = df[pillars].mean(axis=1)
    
    # 2. Estimate Gamma (Deprivation Coefficient) using 2021 data
    print("Estimating Deprivation Coefficient (Gamma)...")
    df_2021 = df[df["year"] == 2021].copy()
    
    # Simple linear regression: patient_volume ~ omi_composite
    valid_data = df_2021.dropna(subset=["omi_composite", "patient_volume"])
    x = valid_data["omi_composite"].values
    y = valid_data["patient_volume"].values
    
    if len(x) > 1 and np.var(x) > 0:
        slope, intercept = np.polyfit(x, y, 1)
        mean_v = np.mean(y)
        gamma = abs(slope) / max(mean_v, 1.0)
        gamma = min(max(gamma, 0.05), 0.5) # Clamp to reasonable range
    else:
        gamma = 0.30 
        
    print(f"Estimated Gamma: {gamma:.4f}")
    
    # 3. Expansion and Interpolation
    print("Interpolating OMI scores for 2017-2020...")
    df_16 = df[df["year"] == 2016].set_index("DAUID")
    df_21 = df[df["year"] == 2021].set_index("DAUID")
    
    # Use 2021 as the master list to ensure validation set completeness
    master_da_list = df_21.index
    
    all_rows = []
    
    for dauid in master_da_list:
        val_21 = df_21.loc[dauid]
        v21 = val_21["patient_volume"]
        omi21 = val_21["omi_composite"]
        
        # Check if 2016 data exists; if not, use 2021 values as the historical baseline
        if dauid in df_16.index:
            val_16 = df_16.loc[dauid]
        else:
            val_16 = val_21
            
        for year in range(2016, 2022):
            frac = (year - 2016) / 5.0
            
            row = {"DAUID": dauid, "year": year}
            for p in pillars:
                # Interpolate if 16 exists, otherwise it stays constant at 21 value
                row[p] = val_16[p] + frac * (val_21[p] - val_16[p])
            
            omi_t = sum(row[p] for p in pillars) / 4.0
            row["omi_composite"] = omi_t
            
            if year == 2021:
                row["patient_volume"] = v21
                row["source"] = "observed"
            else:
                p2021 = v21
                expected = max(0.05, float(p2021 * (1 - gamma * (omi21 - omi_t))))
                
                np.random.seed(int(str(dauid)[:8]) + year)
                row["patient_volume"] = np.random.poisson(expected)
                row["source"] = "synthetic"
                
            all_rows.append(row)
            
    final_df = pd.DataFrame(all_rows)
    
    # Save Outputs
    print("Saving yearly files (Training 2016-2020, Validation 2021)...")
    for year in sorted(final_df["year"].unique()):
        year_df = final_df[final_df["year"] == year]
        
        if year == 2021:
            file_path = processed_dir / "ml_validation_2021.csv"
        else:
            file_path = processed_dir / f"ml_train_{year}.csv"
            
        year_df.to_csv(file_path, index=False)
        print(f" - Saved: {file_path.name}")

    # Also save the combined training set for convenience
    training_set_path = processed_dir / "ml_train_synthetic_combined.csv"
    final_df.to_csv(training_set_path, index=False)
    
    print(f"\nSuccess! All synthetic data saved to {processed_dir}")
    print(f"Total rows (combined): {len(final_df)}")

if __name__ == "__main__":
    main()
