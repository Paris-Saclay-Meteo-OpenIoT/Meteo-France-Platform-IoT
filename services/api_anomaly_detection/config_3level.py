"""
Configuration for 3-Level Weather Anomaly Detection
=====================================================
"""
# ============================================================================
# DATA PATHS
# ============================================================================

DATA_CONFIG = {
    "input_parquet": "weather_data.parquet",
    "output_prefix": "weather_anomalies_complete",
    "output_dir": "outputs",
}

# ============================================================================
# VARIABLE TIERS
# ============================================================================

TIER1_VARS = ["T", "TN", "TX", "RR1"]
TIER2_VARS = ["FF", "FXI", "TD", "U"]

CORE_VARS = TIER1_VARS + TIER2_VARS
COHERENT_VARS = TIER1_VARS

MIN_STATION_FILL_RATE = 0.50

# ============================================================================
# VARIABLES EXEMPT FROM STUCK SENSOR DETECTION
# ============================================================================
# RR1 naturally reports 0.0 for most hours (no rain) — this is NOT a stuck
# sensor. Including it causes ~99% of observations to be flagged as stuck.
STUCK_EXEMPT_VARS = ["RR1"]

# ============================================================================
# MINIMUM DENOMINATOR FLOORS
# ============================================================================
# These floors represent the minimum meaningful spread for each variable.

MIN_SPREAD = {
    "T":    0.5,    # 0.5°C — temperature varies at least this much among neighbours
    "TN":   0.5,    # 0.5°C
    "TX":   0.5,    # 0.5°C
    "TD":   0.5,    # 0.5°C
    "U":    2.0,    # 2% relative humidity
    "FF":   0.3,    # 0.3 m/s wind speed
    "FXI":  0.5,    # 0.5 m/s max gust
    "RR1":  0.2,    # 0.2 mm precipitation
    "PSTAT": 0.5,   # 0.5 hPa
}

# Maximum absolute z-score (cap to prevent score explosion)
Z_SCORE_CAP = 50.0

# ============================================================================
# STATIONS TO EXCLUDE
# ============================================================================
EXCLUDE_STATIONS = [20031400]

# # ============================================================================
# # METADATA COLUMNS
# # ============================================================================
# METADATA_COLS = {
#     "station_id": "NUM_POSTE",
#     "latitude": "LAT",
#     "longitude": "LON",
#     "altitude": "ALTI",
#     "timestamp": "AAAAMMJJHH",
# }

# ============================================================================
# LEVEL 1: SPATIAL
# ============================================================================
SPATIAL_CONFIG = {
    "k_neighbors": 20,
    "max_distance_km": 150,
    "max_altitude_diff_m": 1500,
    "min_neighbors": 2,
}

# ============================================================================
# LEVEL 2: TEMPORAL
# ============================================================================
TEMPORAL_CONFIG = {
    "rolling_hours": 24,
    "min_rolling_periods": 6,
    "max_jump_gap_hours": 3,
    "stuck_threshold": 0.01,
    "stuck_min_periods": 6,
    "drift_window": 48,
}

# ============================================================================
# LEVEL 3: COMBINED
# ============================================================================
COMBINED_CONFIG = {
    "weight_temporal": 0.7,
    "weight_spatial": 0.3,
    "persistence_hours": 6,
    "persistence_threshold": 0.7,
}

# ============================================================================
# ANOMALY DETECTION THRESHOLDS
# ============================================================================
ANOMALY_CONFIG = {
    "epsilon": 1e-6,
    "min_anomalous_vars": 2,
    "sensitivity_profiles": {
        "low":    {"z_warning": 6.0, "z_critical": 8.0, "min_vars": 1},
        "medium": {"z_warning": 5.0, "z_critical": 7.0, "min_vars": 2},
        "high":   {"z_warning": 4.0, "z_critical": 6.0, "min_vars": 2},
    },
}

# # ============================================================================
# # VALIDATION
# # ============================================================================
# VALIDATION_CONFIG = {
#     "min_stations": 10,
#     "min_observations_per_station": 100,
#     "valid_ranges": {
#         "T": (-50, 50), "TN": (-50, 50), "TX": (-50, 50),
#         "TD": (-60, 40), "U": (0, 100),
#         "FF": (0, 50), "FXI": (0, 80), "RR1": (0, 200),
#     },
# }

# # ============================================================================
# # FEATURE FLAGS
# # ============================================================================
# FEATURE_FLAGS = {
#     "enable_spatial": True,
#     "enable_temporal": True,
#     "enable_combined": True,
#     "enable_persistence_check": True,
#     "enable_stuck_detection": True,
#     "enable_drift_detection": True,
#     "enable_jump_detection": True,
#     "enable_multivar_check": True,
# }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_detector_config(sensitivity="medium"):
    profile = ANOMALY_CONFIG["sensitivity_profiles"].get(
        sensitivity, ANOMALY_CONFIG["sensitivity_profiles"]["medium"]
    )
    return {
        "parquet_path": DATA_CONFIG["input_parquet"],
        "core_vars": CORE_VARS,
        "coherent_vars": COHERENT_VARS,
        "exclude_stations": EXCLUDE_STATIONS,
        "min_station_fill_rate": MIN_STATION_FILL_RATE,
        "stuck_exempt_vars": STUCK_EXEMPT_VARS,
        "min_spread": MIN_SPREAD,
        "z_score_cap": Z_SCORE_CAP,
        "k_neighbors": SPATIAL_CONFIG["k_neighbors"],
        "max_km": SPATIAL_CONFIG["max_distance_km"],
        "max_alt_diff": SPATIAL_CONFIG["max_altitude_diff_m"],
        "min_neighbors": SPATIAL_CONFIG["min_neighbors"],
        "rolling_hours": TEMPORAL_CONFIG["rolling_hours"],
        "min_rolling_periods": TEMPORAL_CONFIG["min_rolling_periods"],
        "max_jump_gap_hours": TEMPORAL_CONFIG["max_jump_gap_hours"],
        "z_thr_warning": profile["z_warning"],
        "z_thr_critical": profile["z_critical"],
        "min_anomalous_vars": profile["min_vars"],
        "weight_temporal": COMBINED_CONFIG["weight_temporal"],
        "weight_spatial": COMBINED_CONFIG["weight_spatial"],
        "persistence_hours": COMBINED_CONFIG["persistence_hours"],
    }


def get_config_for_level(level):
    cfg = get_detector_config()
    if level == 1:
        cfg["weight_temporal"] = 0.0
        cfg["weight_spatial"] = 1.0
    elif level == 2:
        cfg["weight_temporal"] = 1.0
        cfg["weight_spatial"] = 0.0
    elif level != 3:
        raise ValueError(f"Invalid level: {level}")
    return cfg


if __name__ == "__main__":
    print("Config")
    print(f"  CORE_VARS: {CORE_VARS}")
    print(f"  STUCK_EXEMPT: {STUCK_EXEMPT_VARS}")
    print(f"  MIN_SPREAD: {MIN_SPREAD}")
    print(f"  Z_SCORE_CAP: {Z_SCORE_CAP}")
