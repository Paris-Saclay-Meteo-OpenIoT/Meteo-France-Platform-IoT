"""
Weather Station Complete Anomaly Detection System (3 Levels)
============================================================
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree
# from typing import Dict, List, Tuple, Optional
import logging
import warnings

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

MAD_SCALE = 1.4826


class CompleteAnomalyDetector:

    ID_COL = "NUM_POSTE"
    LAT_COL = "LAT"
    LON_COL = "LON"
    ALT_COL = "ALTI"
    TIME_COL = "AAAAMMJJHH"

    STUCK_THRESHOLD = 0.01
    STUCK_MIN_PERIODS = 6
    DRIFT_WINDOW = 48

    # Default minimum spread per variable
    DEFAULT_MIN_SPREAD = 0.5

    def __init__(
        self,
        parquet_path="weather_data.parquet",
        core_vars=None,
        coherent_vars=None,
        exclude_stations=None,
        min_station_fill_rate=0.50,
        stuck_exempt_vars=None,
        min_spread=None,
        z_score_cap=50.0,
        k_neighbors=20,
        max_km=150,
        max_alt_diff=1500,
        min_neighbors=2,
        rolling_hours=24,
        min_rolling_periods=6,
        max_jump_gap_hours=3,
        z_thr_warning=5.0,
        z_thr_critical=7.0,
        min_anomalous_vars=2,
        weight_temporal=0.7,
        weight_spatial=0.3,
        persistence_hours=6,
        persistence_threshold=0.7,
    ):
        self.parquet_path = parquet_path
        self.core_vars = core_vars or ["T", "TN", "TX", "RR1", "FF", "FXI", "TD", "U"]
        self.coherent_vars = coherent_vars or ["T", "TN", "TX", "RR1"]
        self.exclude_stations = exclude_stations or []
        self.min_station_fill_rate = min_station_fill_rate
        self.stuck_exempt_vars = set(stuck_exempt_vars or ["RR1"])
        self.min_spread = min_spread or {}
        self.z_score_cap = z_score_cap
        self.k_neighbors = k_neighbors
        self.max_km = max_km
        self.max_alt_diff = max_alt_diff
        self.min_neighbors = min_neighbors
        self.rolling_hours = rolling_hours
        self.min_rolling_periods = min_rolling_periods
        self.max_jump_gap_hours = max_jump_gap_hours
        self.z_thr_warning = z_thr_warning
        self.z_thr_critical = z_thr_critical
        self.min_anomalous_vars = min_anomalous_vars
        self.weight_temporal = weight_temporal
        self.weight_spatial = weight_spatial
        self.persistence_hours = persistence_hours
        self.persistence_threshold = persistence_threshold
        self.EPS = 1e-6

        self.df = None
        self.stations = None
        self.neighbors = None
        self.station_vars = None
        self.usable_vars = None

        self.level1_complete = False
        self.level2_complete = False
        self.level3_complete = False

    def _get_min_spread(self, var: str) -> float:
        """Get minimum denominator floor for a variable."""
        return self.min_spread.get(var, self.DEFAULT_MIN_SPREAD)

    def _cap_z(self, series: pd.Series) -> pd.Series:
        """Cap z-scores to ±z_score_cap to prevent explosion."""
        return series.clip(-self.z_score_cap, self.z_score_cap)

    # ====================================================================
    # DATA LOADING
    # ====================================================================

    def load_and_preprocess_data(self) -> pd.DataFrame:
        print("=" * 80)
        print("LOADING AND PREPROCESSING DATA")
        print("=" * 80)

        if self.df is None:
            print(f"\n1. Loading: {self.parquet_path}")
            self.df = pd.read_parquet(self.parquet_path)
        print(f"   Shape: {self.df.shape}")

        if self.exclude_stations:
            before = len(self.df)
            self.df = self.df[~self.df[self.ID_COL].isin(self.exclude_stations)].copy()
            print(f"\n2. Excluded {before - len(self.df):,} rows from: {self.exclude_stations}")

        # Quality codes
        print("\n3. Applying quality codes (nulling Q=2)...")
        n_nulled = 0
        for var in self.core_vars:
            qcol = f"Q{var}"
            if qcol in self.df.columns:
                mask = self.df[qcol] == 2
                if mask.any():
                    self.df.loc[mask, var] = np.nan
                    n_nulled += mask.sum()
        print(f"   Nulled {n_nulled:,} doubtful values")

        # Variable availability
        print("\n4. Variable availability...")
        available = [v for v in self.core_vars if v in self.df.columns]
        self.usable_vars = []
        for var in available:
            mr = self.df[var].isnull().mean()
            ok = mr < 0.50
            print(f"   {var}: {mr*100:.1f}% missing {'✓' if ok else '✗ SKIP'}")
            if ok:
                self.usable_vars.append(var)
        if not self.usable_vars:
            raise ValueError("No usable variables!")

        # Select columns
        needed = [self.ID_COL, self.LAT_COL, self.LON_COL, self.ALT_COL, self.TIME_COL] + self.usable_vars
        self.df = self.df[[c for c in needed if c in self.df.columns]].copy()

        # Timestamp
        self.df[self.TIME_COL] = self.df[self.TIME_COL].astype(str).str.replace(r"\.0$", "", regex=True)
        self.df["timestamp"] = pd.to_datetime(self.df[self.TIME_COL], format="%Y%m%d%H", errors="coerce")

        for c in [self.LAT_COL, self.LON_COL, self.ALT_COL] + self.usable_vars:
            self.df[c] = pd.to_numeric(self.df[c], errors="coerce")

        self.df = self.df.dropna(subset=["timestamp", self.ID_COL, self.LAT_COL, self.LON_COL]).copy()
        self.df = self.df.sort_values([self.ID_COL, "timestamp"]).reset_index(drop=True)

        # Per-station variable discovery
        print("\n5. Per-station variable discovery...")
        self.station_vars = {}
        n_full = n_partial = 0
        for sid in self.df[self.ID_COL].unique():
            sdf = self.df[self.df[self.ID_COL] == sid]
            avail = [v for v in self.usable_vars if sdf[v].notna().mean() >= self.min_station_fill_rate]
            self.station_vars[sid] = avail
            if len(avail) == len(self.usable_vars):
                n_full += 1
            else:
                n_partial += 1
        print(f"   Full: {n_full}, Partial: {n_partial}")

        # Mask structurally missing
        for var in self.usable_vars:
            missing_stations = [s for s, v in self.station_vars.items() if var not in v]
            if missing_stations:
                self.df.loc[self.df[self.ID_COL].isin(missing_stations), var] = np.nan

        print(f"\n   Final: {self.df.shape}, {self.df[self.ID_COL].nunique()} stations")
        print(f"   Date range: {self.df['timestamp'].min()} → {self.df['timestamp'].max()}")
        print(f"   Stuck-exempt vars: {self.stuck_exempt_vars}")
        print(f"   Z-score cap: ±{self.z_score_cap}")
        return self.df

    # ====================================================================
    # LEVEL 1: SPATIAL
    # ====================================================================

    def build_neighborhood_graph(self):
        print("\n" + "=" * 80)
        print("LEVEL 1: SPATIAL")
        print("=" * 80)

        self.stations = (
            self.df[[self.ID_COL, self.LAT_COL, self.LON_COL, self.ALT_COL]]
            .drop_duplicates(subset=[self.ID_COL])
            .set_index(self.ID_COL).sort_index()
        )
        n = len(self.stations)
        coords_rad = np.radians(self.stations[[self.LAT_COL, self.LON_COL]].to_numpy())
        tree = BallTree(coords_rad, metric="haversine")
        k_q = min(self.k_neighbors + 1, n)
        dist_rad, idx = tree.query(coords_rad, k=k_q)
        dist_km = dist_rad * 6371.0

        sids = self.stations.index.to_numpy()
        self.neighbors = {
            sids[i]: [(sids[idx[i, j]], float(dist_km[i, j])) for j in range(1, k_q)]
            for i in range(n)
        }
        self.neighbors = self._filter_neighbors()
        counts = [len(v) for v in self.neighbors.values()]
        print(f"   Neighbours: mean={np.mean(counts):.1f}, min={np.min(counts)}, max={np.max(counts)}")
        return self.neighbors

    def _filter_neighbors(self):
        if self.max_km is None and self.max_alt_diff is None:
            return self.neighbors
        alt = self.stations[self.ALT_COL].to_dict()
        def ok(s, n, d):
            if self.max_km and d > self.max_km: return False
            if self.max_alt_diff:
                a1, a2 = alt.get(s, np.nan), alt.get(n, np.nan)
                if pd.notna(a1) and pd.notna(a2) and abs(a1-a2) > self.max_alt_diff: return False
            return True
        return {s: [(n,d) for n,d in p if ok(s,n,d)] for s,p in self.neighbors.items()}

    def compute_spatial_scores(self):
        print("\n[Step 1.2] Spatial z-scores ")

        neigh_rows = [
            {self.ID_COL: s, "neigh_id": n, "dist_km": d}
            for s, pairs in self.neighbors.items() for n, d in pairs
        ]
        df_neigh = pd.DataFrame(neigh_rows)

        if df_neigh.empty:
            for v in self.usable_vars:
                self.df[f"{v}_z_spat"] = np.nan
            self.df["score_spatial"] = np.nan
            self.level1_complete = True
            return self.df

        for i, var in enumerate(self.usable_vars, 1):
            print(f"   [{i}/{len(self.usable_vars)}] {var} (floor={self._get_min_spread(var)})...")
            obs = self.df[[self.ID_COL, "timestamp", var]].copy()

            merged = df_neigh.merge(
                obs.rename(columns={self.ID_COL: "neigh_id", var: f"{var}_n"}),
                on="neigh_id", how="inner"
            )
            grp = merged.groupby([self.ID_COL, "timestamp"])[f"{var}_n"]
            stats = grp.agg(neigh_med="median", neigh_count="count").reset_index()
            iqr = grp.apply(
                lambda s: np.subtract(*np.percentile(s.dropna(), [75, 25]))
                if len(s.dropna()) >= self.min_neighbors else np.nan
            ).reset_index(name="neigh_iqr")
            stats = stats.merge(iqr, on=[self.ID_COL, "timestamp"], how="left")

            self.df = self.df.merge(
                stats.rename(columns={
                    "neigh_med": f"{var}_neigh_med",
                    "neigh_iqr": f"{var}_neigh_iqr",
                    "neigh_count": f"{var}_neigh_count",
                }), on=[self.ID_COL, "timestamp"], how="left"
            )

            insuf = self.df[f"{var}_neigh_count"] < self.min_neighbors
            self.df.loc[insuf, f"{var}_neigh_med"] = np.nan
            self.df.loc[insuf, f"{var}_neigh_iqr"] = np.nan

            floor = self._get_min_spread(var)
            denom = self.df[f"{var}_neigh_iqr"].clip(lower=floor)

            self.df[f"{var}_z_spat"] = self._cap_z(
                (self.df[var] - self.df[f"{var}_neigh_med"]) / denom
            )

        z_cols = [f"{v}_z_spat" for v in self.usable_vars if f"{v}_z_spat" in self.df.columns]
        self.df["score_spatial"] = self._rowwise_abs_nanmax(z_cols)
        self.level1_complete = True
        print("✓ Level 1 complete!")
        return self.df

    # ====================================================================
    # LEVEL 2: TEMPORAL
    # ====================================================================

    def compute_temporal_scores(self):
        print("\n" + "=" * 80)
        print("LEVEL 2: TEMPORAL")
        print("=" * 80)

        rw = f"{self.rolling_hours}H"
        dw = f"{self.DRIFT_WINDOW}H"
        self.df = self.df.set_index("timestamp")

        for i, var in enumerate(self.usable_vars, 1):
            floor = self._get_min_spread(var)
            is_exempt = var in self.stuck_exempt_vars
            print(f"   [{i}/{len(self.usable_vars)}] {var} (floor={floor}"
                  f"{', stuck-exempt' if is_exempt else ''})...")

            g = self.df.groupby(self.ID_COL)[var]

            # Diff with gap guard
            self.df[f"{var}_diff1"] = g.diff(1)
            td = self.df.groupby(self.ID_COL).apply(
                lambda x: x.index.to_series().diff().dt.total_seconds() / 3600
            ).droplevel(0)
            self.df.loc[td > self.max_jump_gap_hours, f"{var}_diff1"] = np.nan

            # Rolling stats
            self.df[f"{var}_roll_med"] = g.transform(
                lambda s: s.rolling(rw, min_periods=self.min_rolling_periods).median()
            )
            self.df[f"{var}_roll_mad"] = g.transform(
                lambda s: s.rolling(rw, min_periods=self.min_rolling_periods)
                .apply(self._scaled_mad, raw=True)
            )
            self.df[f"{var}_roll_std"] = g.transform(
                lambda s: s.rolling(rw, min_periods=self.min_rolling_periods).std()
            )

            # FLOOR the MAD denominator
            mad_denom = self.df[f"{var}_roll_mad"].clip(lower=floor)
            std_denom = self.df[f"{var}_roll_std"].clip(lower=floor)

            # Temporal z-score
            self.df[f"{var}_z_temp"] = self._cap_z(
                (self.df[var] - self.df[f"{var}_roll_med"]) / mad_denom
            )

            # Jump z-score
            self.df[f"{var}_jump_z"] = self._cap_z(
                self.df[f"{var}_diff1"].abs() / std_denom
            )

            # Stuck detection
            if is_exempt:
                self.df[f"{var}_is_stuck"] = False
            else:
                self.df[f"{var}_is_stuck"] = g.transform(
                    lambda s: self._detect_stuck(s)
                ).fillna(False).astype(bool)

            # Drift
            self.df[f"{var}_drift"] = g.transform(
                lambda s: s.rolling(dw, min_periods=self.min_rolling_periods)
                .apply(lambda x: x[-1] - x[0] if len(x) > 1 else np.nan, raw=True)
            )
            drift_std = g.transform(
                lambda s: s.rolling(dw, min_periods=self.min_rolling_periods).std()
            ).clip(lower=floor)
            self.df[f"{var}_drift_z"] = self._cap_z(
                self.df[f"{var}_drift"].abs() / drift_std
            )

        self.df = self.df.reset_index()

        # Combine
        print("\n   Combining temporal scores...")
        z_t = [f"{v}_z_temp" for v in self.usable_vars if f"{v}_z_temp" in self.df.columns]
        j_c = [f"{v}_jump_z" for v in self.usable_vars if f"{v}_jump_z" in self.df.columns]
        d_c = [f"{v}_drift_z" for v in self.usable_vars if f"{v}_drift_z" in self.df.columns]

        self.df["score_temporal_deviation"] = self._rowwise_abs_nanmax(z_t)
        self.df["score_temporal_jump"] = self._rowwise_abs_nanmax(j_c)
        self.df["score_temporal_drift"] = self._rowwise_abs_nanmax(d_c)

        stuck_cols = [f"{v}_is_stuck" for v in self.usable_vars if f"{v}_is_stuck" in self.df.columns]
        self.df["is_stuck_any"] = self.df[stuck_cols].any(axis=1) if stuck_cols else False

        self.df["score_temporal"] = np.maximum.reduce([
            self.df["score_temporal_deviation"].fillna(0),
            self.df["score_temporal_jump"].fillna(0),
            self.df["score_temporal_drift"].fillna(0),
        ])

        if self.df["is_stuck_any"].any():
            self.df.loc[self.df["is_stuck_any"], "score_temporal"] = np.maximum(
                self.df.loc[self.df["is_stuck_any"], "score_temporal"],
                self.z_thr_warning,
            )

        n_stuck = self.df["is_stuck_any"].sum()
        print(f"   Stuck sensors: {n_stuck:,} ({100*n_stuck/len(self.df):.2f}%)")
        self.level2_complete = True
        print("✓ Level 2 complete!")
        return self.df

    @staticmethod
    def _scaled_mad(x):
        v = x[~np.isnan(x)]
        if len(v) < 2: return np.nan
        return np.median(np.abs(v - np.median(v))) * MAD_SCALE

    def _detect_stuck(self, s):
        rs = s.rolling(f"{self.STUCK_MIN_PERIODS}H", min_periods=self.STUCK_MIN_PERIODS).std()
        rc = s.rolling(f"{self.STUCK_MIN_PERIODS}H", min_periods=1).count()
        return (rs < self.STUCK_THRESHOLD) & (rc >= self.STUCK_MIN_PERIODS)

    # ====================================================================
    # LEVEL 3: COMBINED
    # ====================================================================

    def compute_combined_scores(self):
        print("\n" + "=" * 80)
        print("LEVEL 3: COMBINED")
        print("=" * 80)

        if not (self.level1_complete and self.level2_complete):
            raise RuntimeError("Must complete Level 1 and 2 first!")

        self.df["score_combined"] = (
            self.weight_temporal * self.df["score_temporal"].fillna(0)
            + self.weight_spatial * self.df["score_spatial"].fillna(0)
        )
        self.df["score_final"] = self.df["score_combined"]

        print(f"   Weights: temporal={self.weight_temporal}, spatial={self.weight_spatial}")

        # Persistence
        self.df["is_persistent"] = self._check_persistence()

        # Multi-var check
        self.df = self._apply_multivar_check()

        # Severity
        self.df["severity"] = self._assign_severity()

        # Report
        n = len(self.df)
        for s in ["OK", "WARNING", "CRITICAL"]:
            c = (self.df["severity"] == s).sum()
            print(f"   {s:>8}: {c:>12,} ({100*c/n:.2f}%)")

        anoms = self.df[self.df["severity"].isin(["WARNING", "CRITICAL"])]
        if len(anoms) > 0:
            print(f"\n   Anomalies: {len(anoms):,} ({100*len(anoms)/n:.2f}%)")
            print(f"   Persistent: {anoms['is_persistent'].sum():,}")
            print(f"   Stuck: {anoms['is_stuck_any'].sum():,}")

        self.level3_complete = True
        print("✓ Level 3 complete!")
        return self.df

    def _check_persistence(self):
        flag = (
            (self.df["score_spatial"].fillna(0) >= self.z_thr_warning)
            | (self.df["score_temporal"].fillna(0) >= self.z_thr_warning)
        ).astype(float)
        win = f"{self.persistence_hours}H"
        mp = max(1, int(self.persistence_hours * self.persistence_threshold))
        self.df["_f"] = flag
        self.df = self.df.set_index("timestamp")
        rate = self.df.groupby(self.ID_COL)["_f"].transform(
            lambda s: s.rolling(win, min_periods=mp).mean()
        )
        self.df = self.df.reset_index()
        result = (rate >= self.persistence_threshold).values
        self.df.drop(columns=["_f"], inplace=True)
        return result

    def _assign_severity(self):
        sev = pd.Series("OK", index=self.df.index)
        sev[self.df["score_final"] >= self.z_thr_warning] = "WARNING"
        sev[self.df["score_final"] >= self.z_thr_critical] = "CRITICAL"
        sev[(self.df["score_final"] >= self.z_thr_warning * 0.8) & self.df["is_persistent"] & (sev == "OK")] = "WARNING"
        sev[(self.df["score_final"] >= self.z_thr_critical * 0.8) & self.df["is_persistent"] & (sev != "CRITICAL")] = "CRITICAL"
        sev[self.df["is_stuck_any"] & (sev == "OK")] = "WARNING"
        return sev

    def _apply_multivar_check(self):
        coherent = [v for v in self.coherent_vars if v in self.usable_vars]
        zs = [f"{v}_z_spat" for v in coherent if f"{v}_z_spat" in self.df.columns]
        zt = [f"{v}_z_temp" for v in coherent if f"{v}_z_temp" in self.df.columns]
        if len(zs) < self.min_anomalous_vars:
            print(f"   Skipping multi-var check ({len(zs)} vars)")
            return self.df
        sc = self.df[zs].abs().gt(self.z_thr_warning).sum(axis=1)
        tc = self.df[zt].abs().gt(self.z_thr_warning).sum(axis=1) if zt else 0
        mask = np.maximum(sc, tc) < self.min_anomalous_vars
        self.df.loc[mask, "score_final"] = 0.0
        print(f"   Multi-var downgraded: {mask.sum():,} ({100*mask.sum()/len(self.df):.2f}%)")
        return self.df

    # ====================================================================
    # UTILITIES
    # ====================================================================

    def _rowwise_abs_nanmax(self, cols):
        if not cols: return pd.Series(np.nan, index=self.df.index)
        arr = self.df[cols].to_numpy(dtype="float64", na_value=np.nan)
        return pd.Series(np.nanmax(np.abs(arr), axis=1), index=self.df.index)

    # ====================================================================
    # OUTPUT
    # ====================================================================

    def extract_anomalies(self):
        print("\n" + "=" * 80)
        print("EXTRACTING ANOMALIES")
        print("=" * 80)

        anoms = self.df[self.df["severity"].isin(["WARNING", "CRITICAL"])].copy()
        print(f"   {len(anoms):,} anomalies")

        keep = [
            self.ID_COL, "timestamp", self.LAT_COL, self.LON_COL, self.ALT_COL,
            "score_final", "score_combined", "score_spatial", "score_temporal",
            "score_temporal_deviation", "score_temporal_jump", "score_temporal_drift",
            "severity", "is_persistent", "is_stuck_any",
        ]
        keep += [c for c in self.df.columns if c.endswith(("_z_spat", "_z_temp"))]
        keep += [c for c in self.df.columns if "_jump_z" in c or "_drift_z" in c or "_is_stuck" in c]
        keep += [c for c in self.usable_vars if c in self.df.columns]
        keep += [c for c in self.df.columns if "_neigh_" in c or "_roll_" in c]

        seen = set()
        keep = [c for c in keep if c in self.df.columns and not (c in seen or seen.add(c))]
        anoms = anoms[keep]

        show = [c for c in ["NUM_POSTE","timestamp","score_final","severity","score_spatial","score_temporal","is_persistent","is_stuck_any"] if c in anoms.columns]
        print(f"\n{anoms[show].head(10).to_string()}")
        return anoms

    # ====================================================================
    # FULL PIPELINE
    # ====================================================================

    def run_full_pipeline(self):
        print("\n╔" + "═"*78 + "╗")
        print("║  3-LEVEL ANOMALY DETECTION" + " "*52 + "║")
        print("╚" + "═"*78 + "╝")

        self.load_and_preprocess_data()
        self.build_neighborhood_graph()
        self.compute_spatial_scores()
        self.compute_temporal_scores()
        self.compute_combined_scores()
        anomalies = self.extract_anomalies()

        print(f"\nCOMPLETE — {len(anomalies):,} / {len(self.df):,} ({100*len(anomalies)/len(self.df):.2f}%)")
        return self.df, anomalies


def main():
    from config_3level import get_detector_config
    d = CompleteAnomalyDetector(**get_detector_config(sensitivity="medium"))
    return d.run_full_pipeline()

if __name__ == "__main__":
    df_full, df_anom = main()
