from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_ONMARG_DIR = RAW_DIR / "onmarg"
RAW_CROSSWALK_DIR = RAW_DIR / "crosswalk"
RAW_PATIENTS_DIR = RAW_DIR / "patients"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
QA_DIR = OUTPUTS_DIR / "qa"

DOWNLOADS_DIR = Path.home() / "Downloads"

TARGET_YEAR = 2021
SYNTHETIC_START_YEAR = 2016
SYNTHETIC_END_YEAR = 2021

CANONICAL_ONMARG_COLUMNS = [
    "DAUID",
    "material_deprivation",
    "residential_instability",
    "dependency",
    "ethnic_concentration",
]

ONMARG_DIMENSION_PATTERNS = {
    "material_deprivation": ["deprivation", "material_resources", "materialresource"],
    "residential_instability": ["instability", "households_dwellings", "householddwellings"],
    "dependency": ["dependency", "age_labourforce", "age_laborforce", "agelabourforce"],
    "ethnic_concentration": [
        "ethniccon",
        "ethnic_concentration",
        "racialized_nc_pop",
        "racialized_n_c_pop",
        "racializedncpop",
    ],
}

ONMARG_FILE_PATTERNS = {
    2016: ["*2016*.xlsx", "*2016*.xls", "*index-on-marg*2016*", "*on-marg*2016*"],
    2021: ["*2021*.xlsx", "*2021*.xls", "*index-on-marg*2021*", "*on-marg*2021*", "*index-on-marg 1.xlsx"],
}

CROSSWALK_FILE_PATTERNS = [
    "*crosswalk*.csv",
    "*crosswalk*.xlsx",
    "*crosswalk*.xls",
    "*postal*da*.*",
    "*dauid*postal*.*",
    "*pccf*.*",
]

PATIENT_FILE_PATTERNS = [
    "*patient*.csv",
    "*patient*.xlsx",
    "*patient*.xls",
    "*orn*.csv",
    "*orn*.xlsx",
    "*renal*.csv",
    "*renal*.xlsx",
    "*mckc*.csv",
    "*mckc*.xlsx",
    "*mckc*.xls",
    "*neph*postal*.xlsx",
    "*postal*codes*.xlsx",
]

CROSSWALK_POSTAL_PATTERNS = ["postal", "postcode", "pc6", "fsa_ldu"]
CROSSWALK_DAUID_PATTERNS = ["dauid", "da_uid"]

PATIENT_POSTAL_PATTERNS = ["postal", "postcode", "pc6"]
PATIENT_COUNT_PATTERNS = ["patient_count", "count", "volume", "patients", "n_patients", "num_patients"]
PATIENT_YEAR_PATTERNS = ["year", "fiscal_year", "calendar_year"]

PIPELINE_BLOCKER_MISSING_CROSSWALK = (
    "Postal code -> DAUID crosswalk file not found. "
    "Add it to data/raw/crosswalk/ (or Downloads fallback) and rerun."
)

ALLOW_SYNTHETIC_WORKAROUNDS = True
SYNTHETIC_RANDOM_SEED = 5130
SYNTHETIC_GAMMA = 0.30
