import pandas as pd
import pathlib
import sys
import re

# Add project root to path to allow imports if needed
project_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

def normalize_dauid(value):
    if pd.isna(value): return None
    text = str(value).strip()
    if text.endswith(".0"): text = text[:-2]
    digits = re.sub(r"\D", "", text)
    return digits if digits else None

def standardize_postal(value):
    if pd.isna(value): return None
    text = re.sub(r"[^A-Za-z0-9]", "", str(value).upper())
    if len(text) == 6 and re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", text):
        return text
    return None

def clean_onmarg(path, year):
    print(f"Cleaning ON-Marg {year} from {path.name}...")
    df = pd.read_csv(path)
    
    if year == 2016:
        cols = {
            "DAUID": "DAUID",
            "instability": "Instability_DA16",
            "deprivation": "Deprivation_DA16",
            "dependency": "Dependency_DA16",
            "ethnic_concentration": "Ethniccon_DA16"
        }
    else: # 2021
        cols = {
            "DAUID": "DAUID",
            "instability": "households_dwellings_DA21",
            "deprivation": "material_resources_DA21",
            "dependency": "age_labourforce_DA21",
            "ethnic_concentration": "racialized_NC_pop_DA21"
        }
        
    df = df[list(cols.values())].copy()
    df.columns = [
        "DAUID", 
        "instability", 
        "deprivation", 
        "dependency", 
        "ethnic_concentration"
    ]
    
    df["DAUID"] = df["DAUID"].apply(normalize_dauid)
    df["year"] = year
    return df.dropna(subset=["DAUID"]).drop_duplicates(subset=["DAUID"])

def extract_year(date_str):
    if pd.isna(date_str): return None
    # Assuming DD/MM/YYYY or YYYY-MM-DD
    match = re.search(r"(\d{4})", str(date_str))
    return int(match.group(1)) if match else None

from src.config import (
    RAW_ONMARG_DIR,
    RAW_PATIENT_FILE,
    POSTAL_TO_DAUID_CROSSWALK_PATH,
    PROCESSED_DIR,
    ML_DATA_LONG_PATH
)

def main():
    # Paths (from config)
    raw_onmarg = RAW_ONMARG_DIR
    raw_patients = RAW_PATIENT_FILE
    crosswalk_path = POSTAL_TO_DAUID_CROSSWALK_PATH
    processed_dir = PROCESSED_DIR
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load and Clean ON-Marg (Long)
    om_2016 = clean_onmarg(raw_onmarg / "DA_2016.csv", 2016)
    om_2021 = clean_onmarg(raw_onmarg / "DA_2021.csv", 2021)
    
    # Stack them
    om_long = pd.concat([om_2016, om_2021], ignore_index=True)
    
    # 2. Load and Link Patients
    print("Linking patient data and extracting years...")
    patients = pd.read_csv(raw_patients)
    crosswalk = pd.read_csv(crosswalk_path)
    
    patients["postal_code"] = patients["Postal Code"].apply(standardize_postal)
    patients["year"] = patients["Visit Date"].apply(extract_year)
    
    crosswalk["postal_code"] = crosswalk["postal_code"].apply(standardize_postal)
    
    # Merge patients with crosswalk
    mapped = patients.merge(crosswalk, on="postal_code", how="inner")
    
    # Aggregate volume by DAUID and year
    volume = mapped.groupby(["DAUID", "year"], as_index=False)["Subject ID"].count().rename(
        columns={"Subject ID": "patient_volume"}
    )
    volume["DAUID"] = volume["DAUID"].apply(normalize_dauid)
    
    # 3. Final Merge (OMI + Volume)
    print("Building long-format ML base...")
    # Join volume to the full OMI list
    # Note: Volume years might not match OMI years exactly (e.g. patients in 2025)
    # We will map patient years to the closest OMI year for this simple pipeline
    # 2016-2020 -> 2016 OMI, 2021+ -> 2021 OMI
    
    # Create a mapping for patient years to census years
    volume["census_year"] = volume["year"].apply(lambda y: 2016 if y <= 2018 else 2021)
    
    # Aggregate volume by DAUID and census_year
    volume_census = volume.groupby(["DAUID", "census_year"], as_index=False)["patient_volume"].sum()
    volume_census.rename(columns={"census_year": "year"}, inplace=True)
    
    # Final Join
    ml_data = om_long.merge(volume_census, on=["DAUID", "year"], how="left")
    ml_data["patient_volume"] = ml_data["patient_volume"].fillna(0)
    
    # Save output
    output_file = processed_dir / "ml_data_long.csv"
    ml_data.to_csv(output_file, index=False)
    
    print(f"Success! Long-format ML data saved to {output_file}")
    print(f"Total rows: {len(ml_data)}")
    print(f"Unique DAUIDs: {ml_data['DAUID'].nunique()}")
    print(f"Total mapped patients: {ml_data['patient_volume'].sum()}")

if __name__ == "__main__":
    main()
