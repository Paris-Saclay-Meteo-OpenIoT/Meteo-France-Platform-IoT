# nwptcn.py
# Production-grade temperature forecasting system:
# Prefer NWP, fallback to TCN when missing
# -*- coding: utf-8 -*-


import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import json
import joblib
from typing import Dict, Tuple, Optional
import argparse
import warnings
warnings.filterwarnings('ignore')


# =========================
# Configuration
# =========================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
STATION_ID = 20004002
SEP = ";"
GOOD_Q_VALUES = {0, 1, 9} 


# =========================
# TCN model definition (must match training architecture)
# =========================
class Chomp1d(nn.Module):
    """
    remove padded future part to keep causality
    """
    def __init__(self, chomp_size: int):
        super().__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, :-self.chomp_size] if self.chomp_size > 0 else x


class TemporalBlock(nn.Module):
    """
    TCN temporal block
    """
    def __init__(self, n_in: int, n_out: int, kernel_size: int, dilation: int, dropout: float = 0.1):
        super().__init__()
        padding = (kernel_size - 1) * dilation

        self.conv1 = nn.Conv1d(n_in, n_out, kernel_size, padding=padding, dilation=dilation)
        self.chomp1 = Chomp1d(padding)
        self.relu1  = nn.ReLU()
        self.drop1  = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(n_out, n_out, kernel_size, padding=padding, dilation=dilation)
        self.chomp2 = Chomp1d(padding)
        self.relu2  = nn.ReLU()
        self.drop2  = nn.Dropout(dropout)

        self.down = nn.Conv1d(n_in, n_out, 1) if n_in != n_out else None
        self.relu = nn.ReLU()

    def forward(self, x):
        out = self.drop1(self.relu1(self.chomp1(self.conv1(x))))
        out = self.drop2(self.relu2(self.chomp2(self.conv2(out))))
        res = x if self.down is None else self.down(x)
        return self.relu(out + res)
    

class TCNForecaster(nn.Module):
    """
    temprature_forecast.ipynb's TCN, input (B,L,C)
    """
    def __init__(self, n_features: int, horizon: int,
                 channels=(64, 64, 64, 64, 64, 64),  # default 6, read from meta
                 kernel_size: int = 3, dropout: float = 0.1):
        super().__init__()
        layers = []
        in_ch = n_features
        for i, out_ch in enumerate(channels):
            layers.append(TemporalBlock(in_ch, out_ch, kernel_size, dilation=2**i, dropout=dropout))
            in_ch = out_ch
        self.tcn = nn.Sequential(*layers)
        self.head = nn.Linear(in_ch, horizon)

    def forward(self, x):
        x = x.transpose(1, 2)      # (B,L,C)->(B,C,L)
        z = self.tcn(x)            # (B,hidden,L)
        last = z[:, :, -1]         # (B,hidden)
        return self.head(last)     # (B,H)

# =========================
# NWP quality check
# =========================
def check_nwp_quality(df_nwp: pd.DataFrame, threshold_missing: float = 0.1) -> Tuple[bool, str]:
    """
    Check NWP data quality

    Returns:
        (is_valid, message): whether usable and detailed message
    """
    total = len(df_nwp)
    
    if total == 0:
        return False, "NWP data completely missing"
    
    # Missing values
    missing = df_nwp['t2m_nwp'].isna().sum()
    missing_rate = missing / total
    
    if missing_rate > threshold_missing:
        return False, f"NWP high missing rate: {missing_rate*100:.1f}% (threshold: {threshold_missing*100:.0f}%)"
    
    # Abnormal values (-50 to 60°C)
    temp_values = df_nwp['t2m_nwp'].dropna()
    if len(temp_values) > 0:
        abnormal = ((temp_values < -50) | (temp_values > 60)).sum()
        abnormal_rate = abnormal / len(temp_values)
        
        if abnormal_rate > 0.05:
            return False, f"NWP abnormal values too high: {abnormal_rate*100:.1f}%"
    
    return True, f"NWP quality good (missing rate: {missing_rate*100:.1f}%)"


# =========================
# Data loading
# =========================
def load_observation_history(csv_obs: str, lookback_hours: int = 168) -> pd.DataFrame:
    """Load historical observations (for TCN fallback)"""
    try:
        df = pd.read_csv(csv_obs, sep=SEP, usecols=["AAAAMMJJHH", "NUM_POSTE", "T"])
        df["AAAAMMJJHH"] = pd.to_datetime(df["AAAAMMJJHH"].astype(str), format="%Y%m%d%H", errors="coerce")
        df = df[df["NUM_POSTE"] == STATION_ID].copy()
        df = df.rename(columns={"AAAAMMJJHH": "time", "T": "temperature_obs"})
        df = df.sort_values("time").set_index("time")
        df["temperature_obs"] = df["temperature_obs"].interpolate(method="time", limit_direction="both").ffill().bfill()
        
        # only keep the last `lookback_hours` hours to match TCN input length
        return df.iloc[-lookback_hours:]
    except Exception as e:
        print(f"Warning: Unable to load observation data: {e}")
        return pd.DataFrame()


def load_nwp_future(csv_nwp_future: str) -> pd.DataFrame:
    """Load future NWP forecast"""
    try:
        df = pd.read_csv(csv_nwp_future, parse_dates=["time"]).sort_values("time")
        return df[["time", "t2m_nwp"]]
    except Exception as e:
        raise ValueError(f"Unable to load NWP forecast file: {e}")


# =========================
# TCN fallback prediction
# =========================
def load_TCN_model(model_path: str, scaler_path: str, meta_path: str):
    """
    load temperatur_forecast.ipynb's outputs (weights/scaler/meta)
    """
    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(meta_path)):
        raise FileNotFoundError(f"Need model/scaler/meta: {model_path}, {scaler_path}, {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    scaler = joblib.load(scaler_path)  # StandardScaler

    hparams = meta["tcn_hparams"]
    model = TCNForecaster(
        n_features=len(meta["model_features"]),
        horizon=int(meta["horizon"]),
        channels=tuple(hparams["channels"]),          # matches 6-level model
        kernel_size=int(hparams["kernel_size"]),
        dropout=float(hparams["dropout"])
    ).to(DEVICE)
    state = torch.load(model_path, map_location=DEVICE)
    model.load_state_dict(state)
    model.eval()

    col_median = np.array(meta["col_median"], dtype=np.float32)
    feature_cols = meta["model_features"]
    return model, scaler, col_median, feature_cols, meta


def qc_by_flag_optional(df: pd.DataFrame, var: str, good_values={0, 1, 9}) -> None:
    """
    apply QC only if Q-column exists
    """
    qvar = "Q" + var
    if var in df.columns and qvar in df.columns:
        bad = df[qvar].isna() | (~df[qvar].isin(list(good_values)))
        df.loc[bad, var] = np.nan


def build_TCN_features(df_obs: pd.DataFrame,
                               feature_cols: list,
                               lookback_hours: int,
                               forecast_start_time: pd.Timestamp) -> pd.DataFrame:
    """
    TCN feature pipeline
    """
    df = df_obs.copy()

    # 1) infer base variables from *_miss
    base_vars = [c[:-5] for c in feature_cols if c.endswith("_miss")]
    base_vars = list(dict.fromkeys(base_vars))

    # 2) QC if possible
    for v in base_vars:
        qc_by_flag_optional(df, v, good_values=GOOD_Q_VALUES)

    # 3) physical checks (T/RR1)
    if "T" in df.columns:
        df.loc[(df["T"] < -40) | (df["T"] > 55), "T"] = np.nan
        jump = df["T"].diff().abs()
        df.loc[jump > 10.0, "T"] = np.nan
    if "RR1" in df.columns:
        df.loc[df["RR1"] < 0, "RR1"] = np.nan

    # 4) align to forecast start
    t0 = pd.to_datetime(forecast_start_time, utc=True)
    start = t0 - pd.Timedelta(hours=lookback_hours)
    end   = t0 - pd.Timedelta(hours=1)
    full_idx = pd.date_range(start, end, freq="h", tz="UTC")
    df = df.reindex(full_idx)

    # 5) time cyclic features
    df["hour_sin"] = np.sin(2*np.pi*df.index.hour/24.0)
    df["hour_cos"] = np.cos(2*np.pi*df.index.hour/24.0)
    df["doy_sin"]  = np.sin(2*np.pi*df.index.dayofyear/365.25)
    df["doy_cos"]  = np.cos(2*np.pi*df.index.dayofyear/365.25)

    # 6) wind vector
    if "DD" in df.columns:
        dd_rad = np.deg2rad(df["DD"])
        df["DD_sin"] = np.sin(dd_rad)
        df["DD_cos"] = np.cos(dd_rad)
    if "FF" in df.columns and "DD_sin" in df.columns:
        df["wind_u"] = df["FF"] * df["DD_sin"]
        df["wind_v"] = df["FF"] * df["DD_cos"]

    # 7) missing masks before filling
    for v in base_vars:
        if v not in df.columns:
            df[v] = np.nan
            df[f"{v}_miss"] = 1.0
        else:
            df[f"{v}_miss"] = df[v].isna().astype("float32")

    # 8) fill missing like StageA
    for v in base_vars:
        df[v] = df[v].interpolate(method="time", limit=3)
        df[v] = df[v].ffill(limit=12).bfill(limit=12)

    # 9) ensure all features exist
    for c in feature_cols:
        if c not in df.columns:
            df[c] = np.nan

    return df[feature_cols]


def pure_tcn_predict(csv_obs: str,
                     horizon_hours: int,
                     input_hours: int,
                     model_path: str,
                     scalers_path: str,
                     meta_path: str,
                     forecast_start_time: Optional[pd.Timestamp] = None) -> np.ndarray:
    """
    pure TCN fallback (output in °C, no inverse_transform)
    """
    model, scaler, col_median, feature_cols, meta = load_TCN_model(model_path, scalers_path, meta_path)

    # load observations
    df_obs = pd.read_csv(csv_obs, sep=SEP)
    df_obs["AAAAMMJJHH"] = pd.to_datetime(df_obs["AAAAMMJJHH"].astype(str), format="%Y%m%d%H", errors="coerce", utc=True)
    df_obs = df_obs[df_obs["NUM_POSTE"] == STATION_ID].copy()
    df_obs = df_obs.sort_values("AAAAMMJJHH").set_index("AAAAMMJJHH")

    # align forecast start to NWP start if provided
    if forecast_start_time is None:
        forecast_start_time = df_obs.index.max() + pd.Timedelta(hours=1)

    feat_df = build_TCN_features(
        df_obs=df_obs,
        feature_cols=feature_cols,
        lookback_hours=input_hours,
        forecast_start_time=forecast_start_time
    )

    X2 = feat_df.values.astype(np.float32)        # (L,C)

    # Fill remaining NaNs with train medians
    nan_mask = np.isnan(X2)
    if nan_mask.any():
        cols = np.where(nan_mask)[1]
        X2[nan_mask] = col_median[cols]

    # scale with single StandardScaler
    X2s = scaler.transform(X2).astype(np.float32)

    # model input (B,L,C)
    x = torch.tensor(X2s[None, :, :], dtype=torch.float32).to(DEVICE)
    with torch.no_grad():
        y = model(x).cpu().numpy().reshape(-1)    # (H,)

    return y[:horizon_hours]


# =========================
# Main production forecast
# =========================
def production_forecast(csv_obs: str, csv_nwp_future: str,
                       tcn_model_path: str, tcn_scalers_path: str, tcn_meta_path: str,
                       input_days: int = 7, horizon_days: int = 7,
                       nwp_missing_threshold: float = 0.1) -> pd.DataFrame:
    """
    Production-grade forecasting system

    Strategy:
    1. Prefer NWP forecast
    2. Check NWP quality (missing rate, abnormal values)
    3. If NWP unusable → fallback to TCN
    4. Return forecast results + method used

    Returns:
        DataFrame: [time, temperature_forecast, forecast_method, confidence]
    """
    
    print("="*70)
    print("production-grade temperature prediction system")
    print("="*70)
    
    input_hours = input_days * 24
    horizon_hours = horizon_days * 24
    
    # 1. load NWP forecast
    print("\nloading NWP forecast...")
    try:
        df_nwp_future = load_nwp_future(csv_nwp_future)
        print(f"NWP forecast length: {len(df_nwp_future)} hours")
    except Exception as e:
        print(f"cannot load NWP forecast: {e}")
        raise
    
    # 2. check NWP quality
    print("\nchecking NWP data quality...")
    is_nwp_valid, nwp_message = check_nwp_quality(df_nwp_future, nwp_missing_threshold)
    print(f"  {nwp_message}")
    
    # 3. Decision: use NWP or fallback to TCN
    if is_nwp_valid:
        print("\nDecision: Use NWP forecast")
        print(" Reason: NWP data quality is good")
        
        # treat missing values (if any) with interpolation
        df_result = df_nwp_future.copy()
        df_result = df_result.rename(columns={"t2m_nwp": "temperature_forecast"})
        
        if df_result['temperature_forecast'].isna().any():
            print(f" fill {df_result['temperature_forecast'].isna().sum()} missing NWP values with linear interpolation")
            df_result['temperature_forecast'] = df_result['temperature_forecast'].interpolate(method='linear')
        
        df_result['forecast_method'] = 'NWP'
        df_result['confidence'] = 'high'
        
    else:
        print("\nDecision: Fallback to Pure TCN temperature model")

        if (not os.path.exists(tcn_model_path)) or (not os.path.exists(tcn_scalers_path)) or (not os.path.exists(tcn_meta_path)):
            raise FileNotFoundError(
                f"Pure TCN model not found: need {tcn_model_path} and {tcn_scalers_path} and {tcn_meta_path}"
            )

        forecast_start = pd.to_datetime(df_nwp_future["time"].iloc[0], utc=True)

        temp_pred = pure_tcn_predict(
            csv_obs=csv_obs,
            horizon_hours=horizon_hours,
            input_hours=input_hours,
            model_path=tcn_model_path,
            scalers_path=tcn_scalers_path,
            meta_path=tcn_meta_path,
            forecast_start_time=forecast_start
        )

        df_result = df_nwp_future[["time"]].copy()
        df_result["temperature_forecast"] = temp_pred[:len(df_result)]
        df_result["forecast_method"] = "Pure_TCN_Fallback"
        df_result["confidence"] = "medium"
    
    # 4. add forecast time
    df_result['forecast_time'] = pd.Timestamp.now()
    
    # 5. limit to horizon
    df_result = df_result.head(horizon_hours)
    
    print(f"\nrediction completed")
    print(f"  Prediction length: {len(df_result)} hours")
    print(f"  Method used: {df_result['forecast_method'].iloc[0]}")
    print(f"  Confidence: {df_result['confidence'].iloc[0]}")
    
    return df_result


# =========================
# Hybrid forecast (partial NWP missing)
# =========================
def hybrid_forecast(csv_obs, csv_nwp_future,
                    tcn_model_path, tcn_scalers_path,tcn_meta_path,
                    input_days=7, horizon_days=7):

    input_hours = input_days * 24
    horizon_hours = horizon_days * 24

    df_nwp_future = load_nwp_future(csv_nwp_future)
    df_result = df_nwp_future.copy()
    df_result["temperature_forecast"] = df_result["t2m_nwp"]

    missing_mask = df_result["temperature_forecast"].isna()

    if missing_mask.sum() == 0:
        df_result["forecast_method"] = "NWP"
        df_result["confidence"] = "high"
        return df_result.head(horizon_hours)

    print("Using Pure TCN for missing timestamps")

    # predict with TCN for missing timestamps
    forecast_start = pd.to_datetime(df_nwp_future["time"].iloc[0], utc=True)
    temp_pred = pure_tcn_predict(
        csv_obs=csv_obs,
        horizon_hours=horizon_hours,
        input_hours=input_hours,
        model_path=tcn_model_path,
        scalers_path=tcn_scalers_path,
        meta_path=tcn_meta_path,
        forecast_start_time=forecast_start
    )

    df_result.loc[missing_mask, "temperature_forecast"] = temp_pred[missing_mask]
    df_result.loc[missing_mask, "forecast_method"] = "Pure_TCN_Fallback"
    df_result.loc[~missing_mask, "forecast_method"] = "NWP"

    df_result["confidence"] = "high"
    df_result.loc[missing_mask, "temperature_forecast"] = temp_pred[missing_mask]

    return df_result.head(horizon_hours)


# =========================
# Rain level classification 
# =========================
def compute_rain_levels(df):
    #basic probability
    P_rain = df["rain_probability"] / 100.0

    df["P_rain"] = P_rain
    df["P_moderate"] = np.where(
        df["rain_mm"] >= 2.5,
        P_rain,
        0.0
    )
    df["P_heavy"] = np.where(
        df["rain_mm"] >= 7.6,
        P_rain,
        0.0
    )

    # labels
    def classify(r):
        if r < 0.1:
            return "No rain"
        elif r < 2.5:
            return "Light rain"
        elif r < 7.6:
            return "Moderate rain"
        else:
            return "Heavy rain"

    df["rain_label"] = df["rain_mm"].apply(classify)

    return df


def update_nwp_forecast(lat=41.918, lon=8.792667, days=7):
    import requests
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"hourly=temperature_2m,precipitation,precipitation_probability&"
        f"forecast_days={days}&timezone=GMT"
    )
    r = requests.get(url, timeout=10)
    data = r.json()

    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "t2m_nwp": data["hourly"]["temperature_2m"],
        "rain_mm": data["hourly"]["precipitation"],
        "rain_probability": data["hourly"]["precipitation_probability"],
    })

    df["rain_flag"] = (df["rain_mm"] >= 0.1).astype(int)
    df = compute_rain_levels(df)

    df.to_csv("NWP_future_20004002.csv", index=False)
    print("NWP forecast updated")




# =========================
# main
# =========================
def main():
    parser = argparse.ArgumentParser(description="Production-level temperature prediction system")
    parser.add_argument("--csv_obs", type=str, default="H_20_latest-2025-2026.csv")
    parser.add_argument("--csv_nwp_future", type=str, default="NWP_future_20004002.csv")
    parser.add_argument("--tcn_model", type=str, default="./point_weights/tcn_temperature.pt",
                       help="TCN model file path")
    parser.add_argument("--tcn_scalers", type=str, default="./point_weights/scaler.joblib",
                       help="temperature_forecast's scaler.joblib path (StandardScaler)")
    parser.add_argument("--tcn_meta", type=str, default="./point_weights/meta.json",
                       help="temperature_forecast's meta.json path (features/medians/hparams)")
    parser.add_argument("--input_days", type=int, default=7)
    parser.add_argument("--horizon_days", type=int, default=7)
    parser.add_argument("--output", type=str, default="forecast_production.csv")
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "hybrid"],
                       help="Prediction mode: auto=auto select NWP/TCN, hybrid=per-hour hybrid")
    parser.add_argument("--nwp_threshold", type=float, default=0.1,
                       help="NWP allowed maximum missing rate (0-1)")
    
    args = parser.parse_args()
    
    try:
        update_nwp_forecast(days=args.horizon_days)
        if args.mode == "auto":
            # Automatic mode: Determines whether to use NWP or TCN.
            df_forecast = production_forecast(
                args.csv_obs, args.csv_nwp_future,
                args.tcn_model, args.tcn_scalers,args.tcn_meta,
                args.input_days, args.horizon_days,
                args.nwp_threshold
            )
        else:
            # Hybrid mode: decide per timestamp whether to use NWP or TCN
            df_forecast = hybrid_forecast(
                args.csv_obs, args.csv_nwp_future,
                args.tcn_model, args.tcn_scalers,args.tcn_meta,
                args.input_days, args.horizon_days
            )
        
        # save results
        df_forecast.to_csv(args.output, index=False)
        
        print(f"\n" + "="*70)
        print("Preview of forecast results (first 24 hours)")
        print("="*70)
        print(df_forecast.head(24).to_string(index=False))
        
        print(f"\n" + "="*70)
        print("Results saved")
        print("="*70)
        print(f" File: {args.output}")
        
        # Statistical information
        method_counts = df_forecast['forecast_method'].value_counts()
        print(f"\nMethod usage statistics:")
        for method, count in method_counts.items():
            print(f"  {method}: {count} hours ({count/len(df_forecast)*100:.1f}%)")
        
        confidence_counts = df_forecast['confidence'].value_counts()
        print(f"\nConfidence level statistics:")
        for conf, count in confidence_counts.items():
            print(f"  {conf}: {count} hours ({count/len(df_forecast)*100:.1f}%)")
        
        print(f"\nPrediction complete!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())