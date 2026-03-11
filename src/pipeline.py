from __future__ import annotations

import fnmatch
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from src.config import (
    ALLOW_SYNTHETIC_WORKAROUNDS,
    CANONICAL_ONMARG_COLUMNS,
    CROSSWALK_DAUID_PATTERNS,
    CROSSWALK_FILE_PATTERNS,
    CROSSWALK_POSTAL_PATTERNS,
    DOWNLOADS_DIR,
    INTERIM_DIR,
    ONMARG_DIMENSION_PATTERNS,
    ONMARG_FILE_PATTERNS,
    PATIENT_COUNT_PATTERNS,
    PATIENT_FILE_PATTERNS,
    PATIENT_POSTAL_PATTERNS,
    PATIENT_YEAR_PATTERNS,
    PIPELINE_BLOCKER_MISSING_CROSSWALK,
    PROCESSED_DIR,
    PROJECT_ROOT,
    QA_DIR,
    RAW_CROSSWALK_DIR,
    RAW_ONMARG_DIR,
    RAW_PATIENTS_DIR,
    SYNTHETIC_END_YEAR,
    SYNTHETIC_RANDOM_SEED,
    SYNTHETIC_START_YEAR,
    TARGET_YEAR,
)

# ------------------------------
# Basic helpers
# ------------------------------


def ensure_dir(path: Path) -> None:
    """Create a directory (and parents) if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def normalize_col_name(name: str) -> str:
    """Normalize column names to lowercase snake-like format for robust matching."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", str(name).strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_")


def normalize_dauid_value(value: object) -> str | None:
    """Convert DAUID-like values to digit-only strings; return None for invalid values."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    return digits if digits else None


def standardize_postal_code(value: object) -> str | None:
    """Normalize Canadian postal code to A1A1A1 format; return None if invalid."""
    if pd.isna(value):
        return None
    text = re.sub(r"[^A-Za-z0-9]", "", str(value).upper())
    if len(text) != 6:
        return None
    if not re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", text):
        return None
    return text


def list_candidate_files(search_roots: Iterable[Path], patterns: Iterable[str]) -> list[Path]:
    """Return unique files matching any pattern across roots (case-insensitive)."""
    normalized_patterns = [p.lower() for p in patterns]
    seen: set[Path] = set()
    out: list[Path] = []

    for root in search_roots:
        if not root.exists():
            continue
        for candidate in root.iterdir():
            if not candidate.is_file():
                continue
            lower_name = candidate.name.lower()
            if any(fnmatch.fnmatch(lower_name, pat) for pat in normalized_patterns):
                if candidate not in seen:
                    out.append(candidate)
                    seen.add(candidate)

    return out


def prioritize_repo_paths(candidates: list[Path], preferred_suffixes: tuple[str, ...] = ()) -> list[Path]:
    """Sort candidates: in-repo first, preferred suffixes first, then stable name order."""
    suffix_rank = {suffix.lower(): idx for idx, suffix in enumerate(preferred_suffixes)}

    def score(path: Path) -> tuple[int, int, int, str]:
        in_repo = 0 if str(path).startswith(str(PROJECT_ROOT)) else 1
        suffix_score = suffix_rank.get(path.suffix.lower(), len(suffix_rank))
        has_expected_name = 0 if "index-on-marg" in path.name.lower() else 1
        return (in_repo, suffix_score, has_expected_name, path.name.lower())

    return sorted(candidates, key=score)


def read_table(path: Path) -> pd.DataFrame:
    """Load a CSV/XLS/XLSX into pandas."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported table format: {path}")


# ------------------------------
# Patient template setup
# ------------------------------

TEMPLATE_FILE = RAW_PATIENTS_DIR / "patient_2021_template.csv"
PLACEHOLDER_FILE = RAW_PATIENTS_DIR / "patient_2021_placeholder.csv"


def ensure_patient_template_files() -> dict[str, object]:
    """Create starter template/placeholder patient files if they do not exist."""
    ensure_dir(RAW_PATIENTS_DIR)
    template_created = False
    placeholder_created = False

    if not TEMPLATE_FILE.exists():
        pd.DataFrame(columns=["postal_code", "patient_count", "year", "source_flag"]).to_csv(
            TEMPLATE_FILE, index=False
        )
        template_created = True

    if not PLACEHOLDER_FILE.exists():
        pd.DataFrame(
            [
                {"postal_code": "M5V3L9", "patient_count": 3, "year": 2021, "source_flag": "placeholder"},
                {"postal_code": "K1A0B1", "patient_count": 2, "year": 2021, "source_flag": "placeholder"},
                {"postal_code": "L6H1M2", "patient_count": 1, "year": 2021, "source_flag": "placeholder"},
            ]
        ).to_csv(PLACEHOLDER_FILE, index=False)
        placeholder_created = True

    return {
        "template_path": str(TEMPLATE_FILE),
        "placeholder_path": str(PLACEHOLDER_FILE),
        "template_created": template_created,
        "placeholder_created": placeholder_created,
    }


# ------------------------------
# ON-Marg loading + cleaning
# ------------------------------


def discover_onmarg_files() -> dict[int, Path | None]:
    """Find ON-Marg 2016 and 2021 files from project folders, then Downloads fallback."""
    found: dict[int, Path | None] = {2016: None, 2021: None}
    roots = [RAW_ONMARG_DIR, DOWNLOADS_DIR]

    for year in [2016, 2021]:
        candidates = list_candidate_files(roots, ONMARG_FILE_PATTERNS[year])
        ranked = prioritize_repo_paths(candidates, preferred_suffixes=(".xlsx", ".xls"))
        found[year] = ranked[0] if ranked else None

    return found


def _excel_engine(path: Path) -> str | None:
    """Use xlrd for .xls files; default engine for .xlsx."""
    return "xlrd" if path.suffix.lower() == ".xls" else None


def _select_onmarg_sheet(path: Path, year: int) -> str:
    """Pick DA-level sheet for a given ON-Marg year."""
    xls = pd.ExcelFile(path, engine=_excel_engine(path))

    for sn in xls.sheet_names:
        if sn.lower() == f"da_{year}".lower():
            return sn

    for sn in xls.sheet_names:
        n = normalize_col_name(sn)
        if "da" in n and str(year) in n:
            return sn

    for sn in xls.sheet_names:
        probe = pd.read_excel(path, sheet_name=sn, nrows=0, engine=_excel_engine(path))
        if any("dauid" in normalize_col_name(c) for c in probe.columns):
            return sn

    raise RuntimeError(f"Could not identify DA-level sheet for ON-Marg {year}: {path}")


def load_onmarg_year(path: Path, year: int) -> tuple[pd.DataFrame, dict[str, object]]:
    """Load one ON-Marg year and return table with source metadata."""
    sheet = _select_onmarg_sheet(path, year)
    df = pd.read_excel(path, sheet_name=sheet, engine=_excel_engine(path))
    return df, {
        "year": year,
        "source_path": str(path),
        "sheet_name": sheet,
        "detected_columns": [str(c) for c in df.columns],
        "row_count": int(len(df)),
    }


def _pick_dauid_column(columns: list[str]) -> str | None:
    """Find DAUID-like identifier column."""
    for col in columns:
        n = normalize_col_name(col)
        if n == "dauid" or "dauid" in n:
            return col
    return None


def _pick_dimension_column(columns: list[str], patterns: list[str]) -> str | None:
    """Pick best ON-Marg feature column using token matching and non-quantile preference."""
    best_col: str | None = None
    best_score = (-1, -1)

    for col in columns:
        n = normalize_col_name(col)
        hits = sum(1 for p in patterns if p in n)
        if hits == 0:
            continue
        is_quantile = 1 if n.endswith("_q") or "_q_" in n else 0
        score = (hits, -is_quantile)
        if score > best_score:
            best_score = score
            best_col = col

    return best_col


def clean_onmarg(df: pd.DataFrame, year: int) -> tuple[pd.DataFrame, dict[str, str]]:
    """Map ON-Marg raw schema to canonical columns and clean DAUID values."""
    columns = [str(c) for c in df.columns]
    dauid_col = _pick_dauid_column(columns)
    if not dauid_col:
        raise RuntimeError(f"Could not find DAUID column in ON-Marg {year}")

    selected: dict[str, str] = {"DAUID": dauid_col}
    for canonical, pats in ONMARG_DIMENSION_PATTERNS.items():
        chosen = _pick_dimension_column(columns, pats)
        if not chosen:
            raise RuntimeError(f"Could not find ON-Marg dimension '{canonical}' for {year}")
        selected[canonical] = chosen

    out = df[
        [
            selected["DAUID"],
            selected["material_deprivation"],
            selected["residential_instability"],
            selected["dependency"],
            selected["ethnic_concentration"],
        ]
    ].copy()
    out.columns = CANONICAL_ONMARG_COLUMNS

    out["DAUID"] = out["DAUID"].apply(normalize_dauid_value)
    out = out.dropna(subset=["DAUID"]).drop_duplicates(subset=["DAUID"]).reset_index(drop=True)

    for c in CANONICAL_ONMARG_COLUMNS[1:]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    return out, {v: k for k, v in selected.items()}


def save_clean_onmarg(df: pd.DataFrame, year: int) -> Path:
    """Persist cleaned ON-Marg table to interim folder."""
    ensure_dir(INTERIM_DIR)
    out_path = INTERIM_DIR / f"onmarg_{year}_clean.csv"
    df.to_csv(out_path, index=False)
    return out_path


# ------------------------------
# Patient loading + cleaning
# ------------------------------


def _looks_like_patient_file(path: Path) -> bool:
    """Quick schema check to avoid selecting unrelated files as patient source."""
    try:
        probe = read_table(path).head(5)
    except Exception:
        return False

    ncols = [normalize_col_name(c) for c in probe.columns]
    has_postal = any(any(tok in c for tok in PATIENT_POSTAL_PATTERNS) for c in ncols)
    has_signal = any(
        any(tok in c for tok in (PATIENT_COUNT_PATTERNS + PATIENT_YEAR_PATTERNS + ["visit", "subject", "priority", "patient"]))
        for c in ncols
    )
    return has_postal and has_signal


def discover_patient_file() -> tuple[Path, str]:
    """Choose best patient file and classify as real/synthetic/placeholder."""
    candidates = list_candidate_files([RAW_PATIENTS_DIR, DOWNLOADS_DIR], PATIENT_FILE_PATTERNS)
    ranked = prioritize_repo_paths(candidates, preferred_suffixes=(".csv", ".xlsx", ".xls"))

    real: list[Path] = []
    synthetic: list[Path] = []
    placeholder: list[Path] = []

    for path in ranked:
        if not _looks_like_patient_file(path):
            continue
        name = path.name.lower()
        if "template" in name:
            continue
        if "placeholder" in name:
            placeholder.append(path)
        elif "synthetic" in name:
            synthetic.append(path)
        else:
            real.append(path)

    if real:
        return real[0], "real"
    if synthetic:
        return synthetic[0], "synthetic"
    if placeholder:
        return placeholder[0], "placeholder"
    return PLACEHOLDER_FILE, "placeholder"


def _pick_column(columns: list[str], patterns: list[str]) -> str | None:
    """Pick first column matching expected token patterns."""
    for col in columns:
        n = normalize_col_name(col)
        if any(p in n for p in patterns):
            return col
    return None


def load_and_clean_patients(path: Path, source_type: str) -> tuple[pd.DataFrame, dict[str, object]]:
    """Load patient data into canonical fields and apply safe defaults when needed."""
    raw = read_table(path)
    cols = [str(c) for c in raw.columns]

    postal_col = _pick_column(cols, PATIENT_POSTAL_PATTERNS)
    if not postal_col:
        raise RuntimeError("Could not detect postal code column in patient file")

    count_col = _pick_column(cols, PATIENT_COUNT_PATTERNS)
    year_col = _pick_column(cols, PATIENT_YEAR_PATTERNS)
    flag_col = _pick_column(cols, ["source_flag"])

    out = raw.rename(columns={postal_col: "postal_code"}).copy()
    assumptions: list[str] = []

    if count_col:
        out = out.rename(columns={count_col: "patient_count"})
    else:
        out["patient_count"] = 1
        assumptions.append("patient_count column missing; defaulted each row to 1")

    if year_col:
        out = out.rename(columns={year_col: "year"})
    else:
        out["year"] = TARGET_YEAR
        assumptions.append(f"year column missing; defaulted all rows to {TARGET_YEAR}")

    if flag_col:
        out = out.rename(columns={flag_col: "source_flag"})
    else:
        out["source_flag"] = source_type

    out["postal_code"] = out["postal_code"].apply(standardize_postal_code)
    out["patient_count"] = pd.to_numeric(out["patient_count"], errors="coerce")
    out["year"] = pd.to_numeric(out["year"], errors="coerce")

    out = out[["postal_code", "patient_count", "year", "source_flag"]].copy()
    out = out.dropna(subset=["postal_code", "patient_count", "year"]).copy()
    out = out[out["patient_count"] >= 0].copy()
    out["year"] = out["year"].astype(int)

    ensure_dir(INTERIM_DIR)
    out_path = INTERIM_DIR / "patients_clean.csv"
    out.to_csv(out_path, index=False)

    return out, {
        "source_path": str(path),
        "source_type": source_type,
        "used_real_patient_file": source_type == "real",
        "used_synthetic_patient_file": source_type == "synthetic",
        "detected_columns": cols,
        "selected_postal_column": postal_col,
        "selected_count_column": count_col,
        "selected_year_column": year_col,
        "row_count": int(len(out)),
        "assumptions": assumptions,
        "output_path": str(out_path),
    }


# ------------------------------
# Crosswalk loading + synthetic fallback
# ------------------------------


def discover_crosswalk_file() -> Path | None:
    """Find best crosswalk; prefer non-synthetic if both real and synthetic exist."""
    candidates = list_candidate_files([RAW_CROSSWALK_DIR, DOWNLOADS_DIR], CROSSWALK_FILE_PATTERNS)
    ranked = prioritize_repo_paths(candidates, preferred_suffixes=(".csv", ".xlsx", ".xls"))
    ranked = sorted(ranked, key=lambda p: ("synthetic" in p.name.lower(), p.name.lower()))
    return ranked[0] if ranked else None


def _pick_crosswalk_columns(columns: list[str]) -> tuple[str | None, str | None]:
    """Detect postal and DAUID columns in crosswalk input."""
    postal_col = _pick_column(columns, CROSSWALK_POSTAL_PATTERNS)
    dauid_col = _pick_column(columns, CROSSWALK_DAUID_PATTERNS)
    return postal_col, dauid_col


def load_and_clean_crosswalk(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    """Load and normalize crosswalk to canonical columns: postal_code, DAUID."""
    raw = read_table(path)
    cols = [str(c) for c in raw.columns]

    postal_col, dauid_col = _pick_crosswalk_columns(cols)
    if not postal_col or not dauid_col:
        raise RuntimeError(
            "Crosswalk found but required columns were not detected "
            "(need one postal-like and one DAUID-like column)."
        )

    out = raw[[postal_col, dauid_col]].copy()
    out.columns = ["postal_code", "DAUID"]
    out["postal_code"] = out["postal_code"].apply(standardize_postal_code)
    out["DAUID"] = out["DAUID"].apply(normalize_dauid_value)
    out = out.dropna(subset=["postal_code", "DAUID"]).drop_duplicates().reset_index(drop=True)

    ensure_dir(INTERIM_DIR)
    out_path = INTERIM_DIR / "crosswalk_clean.csv"
    out.to_csv(out_path, index=False)

    return out, {
        "source_path": str(path),
        "detected_columns": cols,
        "selected_postal_column": postal_col,
        "selected_dauid_column": dauid_col,
        "row_count": int(len(out)),
        "output_path": str(out_path),
        "is_synthetic": "synthetic" in path.name.lower(),
    }


def _generate_postal_codes(n: int, seed: int) -> list[str]:
    """Generate deterministic synthetic postal codes for fallback mapping."""
    rng = np.random.default_rng(seed)
    letters = np.array(list("ABCEGHJKLMNPRSTVXY"))
    codes: set[str] = set()

    while len(codes) < n:
        chunk = max(1000, n - len(codes))
        a = rng.choice(letters, size=chunk)
        b = rng.integers(0, 10, size=chunk).astype(str)
        c = rng.choice(letters, size=chunk)
        d = rng.integers(0, 10, size=chunk).astype(str)
        e = rng.choice(letters, size=chunk)
        f = rng.integers(0, 10, size=chunk).astype(str)
        for i in range(chunk):
            codes.add(f"{a[i]}{b[i]}{c[i]}{d[i]}{e[i]}{f[i]}")
            if len(codes) == n:
                break

    return sorted(codes)


def _hash_assign_dauid(postal_code: str, dauids: list[str]) -> str:
    """Map a postal code to one DAUID deterministically using seeded hash."""
    digest = hashlib.sha256(f"{postal_code}|{SYNTHETIC_RANDOM_SEED}".encode("utf-8")).hexdigest()
    idx = int(digest[:12], 16) % len(dauids)
    return dauids[idx]


def generate_synthetic_crosswalk(
    onmarg_2021: pd.DataFrame,
    observed_postals: pd.Series | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Create synthetic crosswalk; if patient postals exist, anchor mapping to them."""
    ensure_dir(RAW_CROSSWALK_DIR)

    dauids = sorted(onmarg_2021["DAUID"].dropna().astype(str).unique().tolist())
    strategy = "generated_postals_one_to_one"
    observed_count = 0

    if observed_postals is not None:
        clean = [standardize_postal_code(v) for v in observed_postals.tolist()]
        unique_postals = sorted({v for v in clean if v})
        if unique_postals:
            strategy = "patient_postal_hash_assignment"
            observed_count = len(unique_postals)
            out = pd.DataFrame(
                {
                    "postal_code": unique_postals,
                    "DAUID": [_hash_assign_dauid(pc, dauids) for pc in unique_postals],
                }
            )
        else:
            out = pd.DataFrame({"postal_code": _generate_postal_codes(len(dauids), SYNTHETIC_RANDOM_SEED), "DAUID": dauids})
    else:
        out = pd.DataFrame({"postal_code": _generate_postal_codes(len(dauids), SYNTHETIC_RANDOM_SEED), "DAUID": dauids})

    out_path = RAW_CROSSWALK_DIR / "crosswalk_synthetic_pc_to_dauid.csv"
    out.to_csv(out_path, index=False)

    return out, {
        "source_path": str(out_path),
        "detected_columns": ["postal_code", "DAUID"],
        "selected_postal_column": "postal_code",
        "selected_dauid_column": "DAUID",
        "row_count": int(len(out)),
        "output_path": str(out_path),
        "is_synthetic": True,
        "synthetic_strategy": strategy,
        "observed_postal_count": observed_count,
    }


# ------------------------------
# Mapping, target, and ML base
# ------------------------------

UNMAPPED_FILE = QA_DIR / "unmapped_postal_codes.csv"


def map_patients_to_dauid(
    patients_df: pd.DataFrame,
    crosswalk_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    """Join patient rows to DAUID and write unmapped postal QA table."""
    ensure_dir(QA_DIR)
    mapped = patients_df.merge(crosswalk_df, on="postal_code", how="left")

    unmapped = (
        mapped[mapped["DAUID"].isna()]
        .groupby("postal_code", as_index=False)
        .agg(unmapped_rows=("postal_code", "size"), unmapped_patient_count=("patient_count", "sum"))
        .sort_values("unmapped_patient_count", ascending=False)
    )
    unmapped.to_csv(UNMAPPED_FILE, index=False)

    total_rows = int(len(mapped))
    mapped_rows = int(mapped["DAUID"].notna().sum())
    total_patient_count = float(mapped["patient_count"].sum()) if total_rows else 0.0
    mapped_patient_count = float(mapped.loc[mapped["DAUID"].notna(), "patient_count"].sum()) if total_rows else 0.0

    return mapped, {
        "total_rows": total_rows,
        "mapped_rows": mapped_rows,
        "row_mapping_rate": (mapped_rows / total_rows) if total_rows else 0.0,
        "total_patient_count": total_patient_count,
        "mapped_patient_count": mapped_patient_count,
        "patient_count_mapping_rate": (mapped_patient_count / total_patient_count) if total_patient_count else 0.0,
        "unmapped_postal_codes": int(len(unmapped)),
        "unmapped_output_path": str(UNMAPPED_FILE),
    }


def aggregate_patient_volume(mapped_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Aggregate mapped patient rows into DAUID-level 2021 volume target."""
    in_year = mapped_df[mapped_df["year"] == TARGET_YEAR].dropna(subset=["DAUID"]).copy()
    agg = in_year.groupby("DAUID", as_index=False)["patient_count"].sum().rename(columns={"patient_count": "patient_volume_2021"})

    ensure_dir(INTERIM_DIR)
    out_path = INTERIM_DIR / "patient_volume_by_dauid_2021.csv"
    agg.to_csv(out_path, index=False)

    return agg, {"row_count": int(len(agg)), "output_path": str(out_path)}


def build_ml_base_2021(onmarg_2021: pd.DataFrame, patient_volume_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Create final 2021 ML base table by merging OMI features with 2021 target."""
    merged = onmarg_2021.merge(patient_volume_df, on="DAUID", how="left")
    merged["patient_volume_2021"] = merged["patient_volume_2021"].fillna(0)

    ensure_dir(PROCESSED_DIR)
    out_path = PROCESSED_DIR / "ml_base_2021.csv"
    merged.to_csv(out_path, index=False)

    return merged, {"row_count": int(len(merged)), "output_path": str(out_path)}


# ------------------------------
# Deprivation coefficient + synthetic temporal generation
# ------------------------------


def _composite_score(df: pd.DataFrame) -> pd.Series:
    """Simple OMI composite as mean of four dimensions."""
    return df[["material_deprivation", "residential_instability", "dependency", "ethnic_concentration"]].mean(axis=1)


def estimate_deprivation_coefficient(
    onmarg_2021: pd.DataFrame,
    patient_volume_df: pd.DataFrame,
    *,
    is_true_coefficient: bool,
    reason_not_true: str,
) -> tuple[float, dict[str, object]]:
    """Estimate gamma from linear regression of OMI composite to 2021 patient volume."""
    merged = onmarg_2021.merge(patient_volume_df, on="DAUID", how="left")
    merged["patient_volume_2021"] = merged["patient_volume_2021"].fillna(0)
    merged["omi_composite_2021"] = _composite_score(merged)

    work = merged.dropna(subset=["omi_composite_2021", "patient_volume_2021"]).copy()
    x = work["omi_composite_2021"].astype(float).to_numpy()
    y = work["patient_volume_2021"].astype(float).to_numpy()

    if len(x) < 2 or float(np.var(x)) == 0.0:
        slope = 0.0
        intercept = float(np.mean(y)) if len(y) else 0.0
    else:
        x_mean = float(np.mean(x))
        y_mean = float(np.mean(y))
        slope = float(np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2))
        intercept = y_mean - slope * x_mean

    mean_volume = float(np.mean(y)) if len(y) else 0.0
    gamma_estimate = abs(slope) / max(mean_volume, 1.0)
    gamma_estimate = max(0.0, min(gamma_estimate, 1.0))

    ensure_dir(INTERIM_DIR)
    out_path = INTERIM_DIR / "deprivation_coefficient_estimate.csv"
    pd.DataFrame(
        [
            {
                "coefficient_type": "true" if is_true_coefficient else "demo",
                "gamma_estimate": gamma_estimate,
                "slope": slope,
                "intercept": intercept,
                "rows_used": int(len(work)),
                "mean_patient_volume_2021": mean_volume,
                "reason_not_true": reason_not_true,
            }
        ]
    ).to_csv(out_path, index=False)

    return gamma_estimate, {
        "coefficient_type": "true" if is_true_coefficient else "demo",
        "gamma_estimate": gamma_estimate,
        "slope": slope,
        "intercept": intercept,
        "rows_used": int(len(work)),
        "mean_patient_volume_2021": mean_volume,
        "reason_not_true": reason_not_true,
        "output_path": str(out_path),
    }


def generate_temporal_training_data(
    onmarg_2016: pd.DataFrame,
    onmarg_2021: pd.DataFrame,
    patient_volume_df: pd.DataFrame,
    gamma: float,
    *,
    rng_seed: int,
) -> dict[str, object]:
    """Build synthetic 2016-2020 train set and 2021 holdout using interpolation + Poisson noise."""
    feature_cols = ["material_deprivation", "residential_instability", "dependency", "ethnic_concentration"]

    base_2016 = onmarg_2016[["DAUID"] + feature_cols].rename(columns={c: f"{c}_2016" for c in feature_cols})
    base_2021 = onmarg_2021[["DAUID"] + feature_cols].rename(columns={c: f"{c}_2021" for c in feature_cols})

    merged = base_2021.merge(base_2016, on="DAUID", how="inner").merge(patient_volume_df, on="DAUID", how="left")
    merged["patient_volume_2021"] = merged["patient_volume_2021"].fillna(0).astype(float)

    rng = np.random.default_rng(rng_seed)
    year_span = max(SYNTHETIC_END_YEAR - SYNTHETIC_START_YEAR, 1)
    rows: list[dict[str, object]] = []

    for _, row in merged.iterrows():
        dauid = str(row["DAUID"])
        p2021 = float(row["patient_volume_2021"])

        f16 = {c: float(row[f"{c}_2016"]) for c in feature_cols}
        f21 = {c: float(row[f"{c}_2021"]) for c in feature_cols}

        omi16 = float(np.mean(list(f16.values())))
        omi21 = float(np.mean(list(f21.values())))

        for year in range(SYNTHETIC_START_YEAR, SYNTHETIC_END_YEAR + 1):
            frac = (year - SYNTHETIC_START_YEAR) / year_span
            ft = {c: f16[c] + frac * (f21[c] - f16[c]) for c in feature_cols}
            omi_t = float(np.mean(list(ft.values())))
            expected = max(0.05, float(p2021 * (1 - gamma * (omi21 - omi_t))))

            if year < TARGET_YEAR:
                volume = int(rng.poisson(expected))
                source = "synthetic_backcast"
            else:
                volume = int(round(p2021))
                source = "observed_current_2021_source"

            rows.append(
                {
                    "DAUID": dauid,
                    "year": year,
                    "material_deprivation": ft["material_deprivation"],
                    "residential_instability": ft["residential_instability"],
                    "dependency": ft["dependency"],
                    "ethnic_concentration": ft["ethnic_concentration"],
                    "omi_composite": omi_t,
                    "expected_count": expected,
                    "patient_volume": volume,
                    "volume_source": source,
                }
            )

    history = pd.DataFrame(rows)

    ensure_dir(INTERIM_DIR)
    ensure_dir(PROCESSED_DIR)

    history_out = INTERIM_DIR / "synthetic_patient_volume_by_dauid_2016_2021.csv"
    train_out = PROCESSED_DIR / "ml_train_synthetic_2016_2020.csv"
    val_out = PROCESSED_DIR / "ml_validation_2021_observed.csv"

    history.to_csv(history_out, index=False)
    train = history[history["year"] < TARGET_YEAR].copy()
    train.to_csv(train_out, index=False)

    validation = history[history["year"] == TARGET_YEAR].copy().rename(columns={"patient_volume": "patient_volume_2021"})
    validation.to_csv(val_out, index=False)

    return {
        "history_output_path": str(history_out),
        "train_output_path": str(train_out),
        "validation_output_path": str(val_out),
        "history_rows": int(len(history)),
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "years_in_history": f"{SYNTHETIC_START_YEAR}-{SYNTHETIC_END_YEAR}",
        "target_holdout_year": TARGET_YEAR,
    }


# ------------------------------
# QA reports
# ------------------------------


def _fmt_columns(columns: list[str]) -> str:
    """Pretty-print column names for markdown reports."""
    return "(none)" if not columns else ", ".join(columns)


def ensure_unmapped_file_exists() -> None:
    """Always keep an unmapped-postal output file present for downstream consistency."""
    ensure_dir(QA_DIR)
    if not UNMAPPED_FILE.exists():
        pd.DataFrame(columns=["postal_code", "unmapped_rows", "unmapped_patient_count"]).to_csv(UNMAPPED_FILE, index=False)


def write_schema_summary(context: dict[str, Any]) -> Path:
    """Write source schema summary (where files came from and which columns were seen)."""
    ensure_dir(QA_DIR)
    path = QA_DIR / "schema_summary.md"

    om16 = context.get("onmarg_2016_meta", {})
    om21 = context.get("onmarg_2021_meta", {})
    cw = context.get("crosswalk_meta", {})
    pt = context.get("patients_meta", {})

    lines = [
        "# Schema Summary",
        "",
        "## ON-Marg 2016",
        f"- Source: `{om16.get('source_path', 'not found')}`",
        f"- Sheet: `{om16.get('sheet_name', 'n/a')}`",
        f"- Detected columns: {_fmt_columns(om16.get('detected_columns', []))}",
        "",
        "## ON-Marg 2021",
        f"- Source: `{om21.get('source_path', 'not found')}`",
        f"- Sheet: `{om21.get('sheet_name', 'n/a')}`",
        f"- Detected columns: {_fmt_columns(om21.get('detected_columns', []))}",
        "",
        "## Crosswalk",
        f"- Source: `{cw.get('source_path', 'not found')}`",
        f"- Detected columns: {_fmt_columns(cw.get('detected_columns', []))}",
        "",
        "## Patients",
        f"- Source: `{pt.get('source_path', 'not found')}`",
        f"- Detected columns: {_fmt_columns(pt.get('detected_columns', []))}",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_deprivation_coefficient_report(context: dict[str, Any]) -> Path:
    """Write plain-language coefficient report including demo-vs-true status."""
    ensure_dir(QA_DIR)
    path = QA_DIR / "deprivation_coefficient_report.md"
    coef = context.get("deprivation_coeff_meta", {})
    temporal = context.get("temporal_data_meta", {})

    lines = [
        "# Deprivation Coefficient Report",
        "",
        "This report explains how gamma was estimated and whether it is demo or true.",
        "",
        f"- Coefficient type: `{coef.get('coefficient_type', 'not_generated')}`",
        f"- Gamma estimate: {coef.get('gamma_estimate', 'n/a')}",
        f"- Regression slope: {coef.get('slope', 'n/a')}",
        f"- Regression intercept: {coef.get('intercept', 'n/a')}",
        f"- Rows used: {coef.get('rows_used', 'n/a')}",
        f"- Reason not true (if demo): {coef.get('reason_not_true', 'n/a')}",
        "",
        f"- Train output: `{temporal.get('train_output_path', 'n/a')}`",
        f"- Validation output: `{temporal.get('validation_output_path', 'n/a')}`",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_qa_report(context: dict[str, Any]) -> Path:
    """Write end-to-end QA summary for rows, mapping, assumptions, warnings, and blockers."""
    ensure_dir(QA_DIR)
    path = QA_DIR / "qa_report.md"

    blockers: list[str] = context.get("blockers", [])
    warnings: list[str] = context.get("warnings", [])
    mapping = context.get("mapping_meta", {})
    ml = context.get("ml_base_meta", {})
    patient = context.get("patients_meta", {})
    crosswalk = context.get("crosswalk_meta", {})
    coef = context.get("deprivation_coeff_meta", {})
    temporal = context.get("temporal_data_meta", {})

    lines = [
        "# QA Report",
        "",
        f"Run timestamp: {datetime.now().isoformat(timespec='seconds')}",
        f"Target year: {TARGET_YEAR}",
        "",
        "## Input Row Counts",
        f"- ON-Marg 2016 rows: {context.get('onmarg_2016_meta', {}).get('row_count', 0)}",
        f"- ON-Marg 2021 rows: {context.get('onmarg_2021_meta', {}).get('row_count', 0)}",
        f"- Crosswalk rows (clean): {crosswalk.get('row_count', 0)}",
        f"- Patient rows (clean): {patient.get('row_count', 0)}",
        "",
        "## Mapping Quality",
        f"- Mapping rate (rows): {mapping.get('row_mapping_rate', 0.0):.2%}",
        f"- Mapping rate (patient_count): {mapping.get('patient_count_mapping_rate', 0.0):.2%}",
        f"- Unmapped postal codes: {mapping.get('unmapped_postal_codes', 0)}",
        "",
        "## Final Output",
        f"- Final DAUID row count: {ml.get('row_count', 0)}",
        f"- Patient source type: `{patient.get('source_type', 'unknown')}`",
        f"- Patient source file: `{patient.get('source_path', 'not found')}`",
        "",
        "## Crosswalk Mode",
        f"- Is synthetic crosswalk: {crosswalk.get('is_synthetic', False)}",
        f"- Synthetic strategy: `{crosswalk.get('synthetic_strategy', 'n/a')}`",
        "",
        "## Deprivation Coefficient",
        f"- Coefficient type: `{coef.get('coefficient_type', 'not_generated')}`",
        f"- Gamma estimate: {coef.get('gamma_estimate', 'n/a')}",
        f"- Why not true (if demo): {coef.get('reason_not_true', 'n/a')}",
        "",
        "## Temporal Outputs",
        f"- Train file (2016-2020): `{temporal.get('train_output_path', 'n/a')}`",
        f"- Validation file (2021 holdout): `{temporal.get('validation_output_path', 'n/a')}`",
        f"- Train rows: {temporal.get('train_rows', 'n/a')}",
        f"- Validation rows: {temporal.get('validation_rows', 'n/a')}",
        "",
        "## Warnings",
    ]

    lines.extend([f"- {w}" for w in warnings] if warnings else ["- None"])
    lines.extend(["", "## Blockers"])
    lines.extend([f"- {b}" for b in blockers] if blockers else ["- None"])

    assumptions = patient.get("assumptions", [])
    lines.extend(["", "## Assumptions Applied"])
    lines.extend([f"- {a}" for a in assumptions] if assumptions else ["- None"])

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ------------------------------
# Main orchestration
# ------------------------------


def run_pipeline() -> tuple[dict[str, Any], int]:
    """
    Run full data pipeline end-to-end.

    Flow:
    1) Ensure template files
    2) Load and clean ON-Marg
    3) Load and clean patient file
    4) Resolve crosswalk (real or synthetic)
    5) Map + aggregate + build ML base
    6) Estimate coefficient + generate temporal synthetic outputs
    7) Write QA reports
    """
    context: dict[str, Any] = {"blockers": [], "warnings": []}

    # 1) Ensure patient templates always exist.
    context["patient_templates"] = ensure_patient_template_files()

    # 2) Load and clean ON-Marg files.
    onmarg_files = discover_onmarg_files()
    context["onmarg_files"] = {k: (str(v) if v else None) for k, v in onmarg_files.items()}

    onmarg_2016 = None
    onmarg_2021 = None

    for year in [2016, 2021]:
        path = onmarg_files.get(year)
        if not path:
            context["blockers"].append(f"ON-Marg {year} file not found in data/raw/onmarg/ or Downloads.")
            continue

        try:
            raw_df, meta = load_onmarg_year(path, year)
            clean_df, mapping = clean_onmarg(raw_df, year)
            out_path = save_clean_onmarg(clean_df, year)

            meta["selected_to_canonical_mapping"] = mapping
            meta["clean_output_path"] = str(out_path)
            meta["clean_row_count"] = int(len(clean_df))
            context[f"onmarg_{year}_meta"] = meta

            if year == 2016:
                onmarg_2016 = clean_df
            else:
                onmarg_2021 = clean_df
        except Exception as exc:
            context["blockers"].append(str(exc))

    # 3) Load and clean patient file.
    patients_df = None
    source_type = "placeholder"
    try:
        patient_path, source_type = discover_patient_file()
        patients_df, patients_meta = load_and_clean_patients(patient_path, source_type)
        context["patients_meta"] = patients_meta
    except Exception as exc:
        context["blockers"].append(str(exc))

    # 4) Resolve crosswalk (real if available, otherwise synthetic fallback).
    crosswalk_df = None
    crosswalk_path = discover_crosswalk_file()
    try:
        if crosswalk_path:
            crosswalk_df, crosswalk_meta = load_and_clean_crosswalk(crosswalk_path)
            # If an old synthetic file exists and patient postals are available,
            # rebuild synthetic mapping to match current patient file.
            if (
                crosswalk_meta.get("is_synthetic")
                and ALLOW_SYNTHETIC_WORKAROUNDS
                and onmarg_2021 is not None
                and patients_df is not None
            ):
                crosswalk_df, crosswalk_meta = generate_synthetic_crosswalk(
                    onmarg_2021, observed_postals=patients_df["postal_code"]
                )
                context["warnings"].append("Rebuilt synthetic crosswalk from detected patient postal codes.")
        elif ALLOW_SYNTHETIC_WORKAROUNDS and onmarg_2021 is not None:
            observed = patients_df["postal_code"] if patients_df is not None else None
            crosswalk_df, crosswalk_meta = generate_synthetic_crosswalk(onmarg_2021, observed_postals=observed)
            context["warnings"].append("Crosswalk file not found; generated synthetic crosswalk for development workflow.")
        else:
            raise RuntimeError(PIPELINE_BLOCKER_MISSING_CROSSWALK)

        context["crosswalk_meta"] = crosswalk_meta
    except Exception as exc:
        context["blockers"].append(str(exc))

    # 5) Link and aggregate target, then create ML base.
    patient_volume_df = None
    if patients_df is not None and crosswalk_df is not None and onmarg_2021 is not None:
        mapped_df, mapping_meta = map_patients_to_dauid(patients_df, crosswalk_df)
        context["mapping_meta"] = mapping_meta

        patient_volume_df, pv_meta = aggregate_patient_volume(mapped_df)
        context["patient_volume_meta"] = pv_meta

        _, ml_meta = build_ml_base_2021(onmarg_2021, patient_volume_df)
        context["ml_base_meta"] = ml_meta

    # 6) Estimate gamma and generate temporal synthetic sets.
    if patient_volume_df is not None and onmarg_2016 is not None and onmarg_2021 is not None:
        crosswalk_is_real = bool(crosswalk_df is not None and not context.get("crosswalk_meta", {}).get("is_synthetic", False))
        patient_is_real = bool(context.get("patients_meta", {}).get("used_real_patient_file", False))
        no_assumptions = len(context.get("patients_meta", {}).get("assumptions", [])) == 0

        is_true_coeff = crosswalk_is_real and patient_is_real and no_assumptions
        reasons: list[str] = []
        if not crosswalk_is_real:
            reasons.append("Crosswalk is synthetic or missing.")
        if not patient_is_real:
            reasons.append("Patient file is not designated final ORN source.")
        if not no_assumptions:
            reasons.append("Patient data needed default assumptions (missing patient_count/year).")

        reason_not_true = "All true-data conditions satisfied." if not reasons else " ".join(reasons)
        if reasons:
            context["warnings"].append("Deprivation coefficient is demo-only because true-data conditions are not fully met.")

        gamma, coeff_meta = estimate_deprivation_coefficient(
            onmarg_2021=onmarg_2021,
            patient_volume_df=patient_volume_df,
            is_true_coefficient=is_true_coeff,
            reason_not_true=reason_not_true,
        )
        context["deprivation_coeff_meta"] = coeff_meta

        temporal_meta = generate_temporal_training_data(
            onmarg_2016=onmarg_2016,
            onmarg_2021=onmarg_2021,
            patient_volume_df=patient_volume_df,
            gamma=gamma,
            rng_seed=SYNTHETIC_RANDOM_SEED,
        )
        context["temporal_data_meta"] = temporal_meta

    # 7) Reports
    ensure_unmapped_file_exists()
    write_schema_summary(context)
    write_deprivation_coefficient_report(context)
    write_qa_report(context)

    return context, (1 if context["blockers"] else 0)
