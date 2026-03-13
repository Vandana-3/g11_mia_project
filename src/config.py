from pathlib import Path

# Project Root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Data Directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Source File Paths
RAW_ONMARG_DIR = RAW_DIR / "onmarg"
RAW_PATIENTS_DIR = RAW_DIR / "patients"
RAW_PATIENT_FILE = RAW_PATIENTS_DIR / "mckc_raw.csv"

# Processed File Paths
POSTAL_TO_DAUID_CROSSWALK_PATH = PROCESSED_DIR / "postal_to_dauid_crosswalk.csv"
ML_DATA_LONG_PATH = PROCESSED_DIR / "ml_data_long.csv"

# Simulation Constants
CANONICAL_COLUMNS = ["instability", "deprivation", "dependency", "ethnic_concentration"]
DEFAULT_GAMMA = 0.1151
