import pandas as pd
import requests
import time
import pathlib
import sys

# Add project root to path to allow imports if needed
project_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.config import (
    RAW_PATIENT_FILE,
    POSTAL_TO_DAUID_CROSSWALK_PATH
)

# Geocoding Endpoints
DA_SERVICE_URL = 'https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer/12/query'
GEOCODE_SINGLE_URL = 'https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates'

def geocode_postal(postal_code):
    params = {
        'singleLine': f"{postal_code}, Canada",
        'f': 'json',
        'maxLocations': 1
    }
    try:
        resp = requests.get(GEOCODE_SINGLE_URL, params=params, timeout=15)
        data = resp.json()
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['location']
    except Exception as e:
        print(f"Error geocoding {postal_code}: {e}")
    return None

def get_dauid_at_point(x, y):
    params = {
        'geometry': f"{x},{y}",
        'geometryType': 'esriGeometryPoint',
        'inSR': '4326',
        'spatialRel': 'esriSpatialRelIntersects',
        'outFields': 'DAUID',
        'returnGeometry': 'false',
        'f': 'json'
    }
    try:
        resp = requests.get(DA_SERVICE_URL, params=params, timeout=15)
        data = resp.json()
        if 'features' in data and data['features']:
            return data['features'][0]['attributes']['DAUID']
    except Exception as e:
        print(f"Error querying DA for {x},{y}: {e}")
    return None

def main():
    print(f"Reading patients from {RAW_PATIENT_FILE}...")
    try:
        df = pd.read_csv(RAW_PATIENT_FILE)
    except Exception as e:
        print(f"Failed to read {RAW_PATIENT_FILE}: {e}")
        return

    if 'Postal Code' not in df.columns:
        print(f"Column 'Postal Code' not found. Available: {df.columns.tolist()}")
        return

    unique_postals = df['Postal Code'].dropna().unique().tolist()
    
    mapping = []
    total = len(unique_postals)
    
    print(f"Found {total} unique postal codes. Starting mapping process using ArcGIS and StatCan...")
    
    for i, pc in enumerate(unique_postals):
        pc_clean = str(pc).strip().upper()
        if len(pc_clean) < 6:
            continue
            
        location = geocode_postal(pc_clean)
        dauid = None
        if location:
            dauid = get_dauid_at_point(location['x'], location['y'])
        
        if dauid:
            mapping.append({'postal_code': pc_clean, 'DAUID': dauid})
            print(f"[{i+1}/{total}] {pc_clean} -> {dauid}", flush=True)
        else:
            print(f"[{i+1}/{total}] {pc_clean} -> FAILED", flush=True)
        
        if (i + 1) % 10 == 0:
            time.sleep(1)

    out_df = pd.DataFrame(mapping)
    POSTAL_TO_DAUID_CROSSWALK_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(POSTAL_TO_DAUID_CROSSWALK_PATH, index=False)
    print(f"Saved crosswalk mapping to {POSTAL_TO_DAUID_CROSSWALK_PATH}")

if __name__ == '__main__':
    main()
