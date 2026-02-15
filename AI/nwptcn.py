# nwptcn.py
# Production-grade temperature forecasting system:
# Prefer NWP, fallback to TCN when missing
# -*- coding: utf-8 -*-


import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import pickle
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


# =========================
# TCN model definition (must match training architecture)
# =========================
class CausalConv1d(torch.nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size, dilation=1):
        super().__init__()
        self.pad = (kernel_size - 1) * dilation
        self.conv = torch.nn.Conv1d(in_ch, out_ch, kernel_size, padding=0, dilation=dilation)
    
    def forward(self, x):
        x = torch.nn.functional.pad(x, (self.pad, 0))
        return self.conv(x)


class TemporalBlock(torch.nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size, dilation, dropout=0.1):
        super().__init__()
        self.conv1 = CausalConv1d(in_ch, out_ch, kernel_size, dilation)
        self.relu1 = torch.nn.ReLU()
        self.drop1 = torch.nn.Dropout(dropout)
        
        self.conv2 = CausalConv1d(out_ch, out_ch, kernel_size, dilation)
        self.relu2 = torch.nn.ReLU()
        self.drop2 = torch.nn.Dropout(dropout)
        
        self.downsample = torch.nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else None
    
    def forward(self, x):
        out = self.drop1(self.relu1(self.conv1(x)))
        out = self.drop2(self.relu2(self.conv2(out)))
        res = x if self.downsample is None else self.downsample(x)
        return out + res


class TCNForecaster(nn.Module):
    def __init__(self, in_channels: int, horizon: int,
                 hidden_channels: int = 64, levels: int = 6,
                 kernel_size: int = 3, dropout: float = 0.1):
        super().__init__()
        layers = []
        ch = in_channels
        for i in range(levels):
            layers.append(TemporalBlock(ch, hidden_channels, kernel_size, 2**i, dropout))
            ch = hidden_channels
        self.tcn = nn.Sequential(*layers)
        self.head = nn.Linear(hidden_channels, horizon)

    def forward(self, x):
        h = self.tcn(x)        # [B, hidden, L]
        h_last = h[:, :, -1]   # [B, hidden]
        return self.head(h_last)  # [B, H]
    
FEATURE_COLS = [
    "temperature", "rainfall", "cloud_cover",
    "wind_speed", "humidity", "pressure",
    "rainfall_3h", "hour_sin", "hour_cos",
    "doy_sin", "doy_cos"
]

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
def pure_tcn_predict(csv_obs, horizon_hours, input_hours,
                     model_path, scalers_path):

    df_obs = pd.read_csv(csv_obs, sep=SEP)
    df_obs["AAAAMMJJHH"] = pd.to_datetime(df_obs["AAAAMMJJHH"].astype(str), format="%Y%m%d%H")
    df_obs = df_obs[df_obs["NUM_POSTE"] == STATION_ID].copy()

    df_obs = df_obs.rename(columns={
        "AAAAMMJJHH": "time",
        "T": "temperature",
        "RR1": "rainfall",
        "N": "cloud_cover",
        "FF": "wind_speed",
        "U": "humidity",
        "PSTAT": "pressure"
    }).sort_values("time").set_index("time")

    df_obs["rainfall"] = df_obs["rainfall"].fillna(0.0)

    for c in ["temperature", "cloud_cover", "wind_speed", "humidity", "pressure"]:
        df_obs[c] = df_obs[c].interpolate(method="time", limit_direction="both")

    df_obs["rainfall_3h"] = df_obs["rainfall"].rolling(3, min_periods=1).sum()

    idx = df_obs.index
    df_obs["hour_sin"] = np.sin(2*np.pi*idx.hour/24.0)
    df_obs["hour_cos"] = np.cos(2*np.pi*idx.hour/24.0)
    df_obs["doy_sin"]  = np.sin(2*np.pi*idx.dayofyear/365.25)
    df_obs["doy_cos"]  = np.cos(2*np.pi*idx.dayofyear/365.25)

    model = TCNForecaster(in_channels=len(FEATURE_COLS),
                          horizon=horizon_hours).to(DEVICE)
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.eval()

    with open(scalers_path, "rb") as f:
        scalers = pickle.load(f)

    last_block = df_obs[FEATURE_COLS].iloc[-input_hours:].copy()

    for c in FEATURE_COLS:
        last_block[[c]] = scalers[c].transform(last_block[[c]])

    x = torch.tensor(last_block.values.T,
                     dtype=torch.float32).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        y_scaled = model(x).cpu().numpy().reshape(-1,1)

    return scalers["temperature"].inverse_transform(y_scaled).reshape(-1)


# =========================
# Main production forecast
# =========================
def production_forecast(csv_obs: str, csv_nwp_future: str,
                       tcn_model_path: str, tcn_scalers_path: str,
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

        if not os.path.exists(tcn_model_path) or not os.path.exists(tcn_scalers_path):
            raise FileNotFoundError(
                f"Pure TCN model not found: need {tcn_model_path} and {tcn_scalers_path}"
            )

        temp_pred = pure_tcn_predict(
            csv_obs,
            horizon_hours,
            input_hours,
            tcn_model_path,
            tcn_scalers_path
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
                    tcn_model_path, tcn_scalers_path,
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
    temp_pred = pure_tcn_predict(
        csv_obs,
        horizon_hours,
        input_hours,
        tcn_model_path,
        tcn_scalers_path
    )

    df_result.loc[missing_mask, "temperature_forecast"] = temp_pred[missing_mask]
    df_result.loc[missing_mask, "forecast_method"] = "Pure_TCN_Fallback"
    df_result.loc[~missing_mask, "forecast_method"] = "NWP"

    df_result["confidence"] = "high"
    df_result.loc[missing_mask, "confidence"] = "medium"

    return df_result.head(horizon_hours)


def update_nwp_forecast(lat=41.918, lon=8.792667, days=7):
    import requests
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"hourly=temperature_2m,precipitation&"
        f"forecast_days={days}&timezone=GMT"
    )
    r = requests.get(url, timeout=10)
    data = r.json()

    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "t2m_nwp": data["hourly"]["temperature_2m"],
        "rain_mm": data["hourly"]["precipitation"],
    })

    df["rain_flag"] = (df["rain_mm"] >= 0.1).astype(int)

    df.to_csv("NWP_future_20004002.csv", index=False)
    print("✓ NWP forecast updated")


# =========================
# main
# =========================
def main():
    parser = argparse.ArgumentParser(description="Production-level temperature prediction system")
    parser.add_argument("--csv_obs", type=str, default="H_20_latest-2025-2026.csv")
    parser.add_argument("--csv_nwp_future", type=str, default="NWP_future_20004002.csv")
    parser.add_argument("--tcn_model", type=str, default="tcn_temperature.pt",
                       help="TCN model file path")
    parser.add_argument("--tcn_scalers", type=str, default="tcn_scalers.pkl",
                       help="TCN scalers file path")
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
                args.tcn_model, args.tcn_scalers,
                args.input_days, args.horizon_days,
                args.nwp_threshold
            )
        else:
            # Hybrid mode: decide per timestamp whether to use NWP or TCN
            df_forecast = hybrid_forecast(
                args.csv_obs, args.csv_nwp_future,
                args.tcn_model, args.tcn_scalers,
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