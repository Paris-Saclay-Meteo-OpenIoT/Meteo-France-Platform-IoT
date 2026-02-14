"""
Manual Detection Script
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import json

from complete_anomaly_detector import CompleteAnomalyDetector
from config_3level import get_detector_config

OUTPUT_DIR = Path("frontend_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    print("\n" + "=" * 80)
    print("MANUAL ANOMALY DETECTION")
    print("=" * 80 + "\n")

    data_file = "weather_data.parquet"
    if not Path(data_file).exists():
        print(f"ERROR: {data_file} not found!")
        return

    detector = CompleteAnomalyDetector(**get_detector_config(sensitivity="medium"))
    df_full, df_anomalies = detector.run_full_pipeline()

    print(f"\nTotal observations: {len(df_full):,}")
    print(f"Total anomalies:    {len(df_anomalies):,} "
          f"({100 * len(df_anomalies) / len(df_full):.2f}%)\n")

    print("Exporting for frontend...")
    export_for_frontend(df_full, df_anomalies, detector)
    print(f"\nFiles in: {OUTPUT_DIR}/\n")


def _sf(val):
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def export_for_frontend(df_full, df_anomalies, detector):
    uv = detector.usable_vars or ["T", "TN", "TX", "RR1"]
    detail_vars = [v for v in ["T","TN","TX","RR1","TD","U","FF","FXI"] if v in uv]

    anomalies_list = []
    for _, row in df_anomalies.iterrows():
        a = {
            "station_id": str(row["NUM_POSTE"]),
            "timestamp": row["timestamp"].isoformat(),
            "latitude": float(row["LAT"]),
            "longitude": float(row["LON"]),
            "altitude": _sf(row.get("ALTI")),
            "severity": str(row["severity"]),
            "scores": {"final": _sf(row["score_final"]), "spatial": _sf(row["score_spatial"]), "temporal": _sf(row["score_temporal"])},
            "flags": {"persistent": bool(row.get("is_persistent", False)), "stuck_sensor": bool(row.get("is_stuck_any", False))},
            "variables": {},
        }
        for var in detail_vars:
            if var in row.index:
                a["variables"][var] = {"value": _sf(row.get(var)), "z_spatial": _sf(row.get(f"{var}_z_spat")), "z_temporal": _sf(row.get(f"{var}_z_temp"))}
        anomalies_list.append(a)

    with open(OUTPUT_DIR / "anomalies_current.json", "w") as f:
        json.dump({"update_time": datetime.now().isoformat(), "total_anomalies": len(anomalies_list), "anomalies": anomalies_list}, f, indent=2)

    features = [{"type":"Feature","geometry":{"type":"Point","coordinates":[a["longitude"],a["latitude"]]},"properties":{"station_id":a["station_id"],"timestamp":a["timestamp"],"severity":a["severity"],"score_final":a["scores"]["final"],"score_spatial":a["scores"]["spatial"],"score_temporal":a["scores"]["temporal"],"persistent":a["flags"]["persistent"],"stuck_sensor":a["flags"]["stuck_sensor"]}} for a in anomalies_list]
    with open(OUTPUT_DIR / "anomalies_geo.json", "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

    stations = df_full[["NUM_POSTE","LAT","LON","ALTI"]].drop_duplicates()
    asids = set(df_anomalies["NUM_POSTE"].astype(str))
    sl = [{"station_id":str(r["NUM_POSTE"]),"latitude":float(r["LAT"]),"longitude":float(r["LON"]),"altitude":_sf(r.get("ALTI")),"has_anomaly":str(r["NUM_POSTE"]) in asids,"available_vars":detector.station_vars.get(r["NUM_POSTE"],[])} for _,r in stations.iterrows()]
    with open(OUTPUT_DIR / "stations_info.json", "w") as f:
        json.dump({"update_time": datetime.now().isoformat(), "total_stations": len(sl), "stations": sl}, f, indent=2)

    n_a = len(df_anomalies)
    with open(OUTPUT_DIR / "last_update.json", "w") as f:
        json.dump({"last_update":datetime.now().isoformat(),"version":"4.1","data_time_range":{"start":df_full["timestamp"].min().isoformat(),"end":df_full["timestamp"].max().isoformat()},"variables_used":uv,"statistics":{"total_observations":len(df_full),"total_stations":int(df_full["NUM_POSTE"].nunique()),"total_anomalies":n_a,"anomaly_rate":round(n_a/len(df_full)*100,4),"by_severity":{"WARNING":int((df_anomalies["severity"]=="WARNING").sum()),"CRITICAL":int((df_anomalies["severity"]=="CRITICAL").sum())}}}, f, indent=2)


if __name__ == "__main__":
    main()
