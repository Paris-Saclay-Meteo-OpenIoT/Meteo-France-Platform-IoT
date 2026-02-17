# nwprain.py
# Production-grade rain forecasting system:
# Prefer NWP, fallback to ML model when missing
# -*- coding: utf-8 -*-

import os
import numpy as np
import pandas as pd
import joblib
from typing import Tuple, Dict
import argparse
import warnings
warnings.filterwarnings('ignore')


# =========================
# Configuration
# =========================
STATION_ID = 20004002
HORIZON = 168  # 7 days


# =========================
# NWP rain data quality check
# =========================
def check_nwp_rain_quality(df_nwp: pd.DataFrame, 
                           threshold_missing: float = 0.1) -> Tuple[bool, str]:
    """
    Check NWP rain forecast quality
    
    Required columns:
    - rain_mm: rain forecast
    - rain_probability or P_rain: rain probability
    - rain_label: rain level label
    
    Returns:
        (is_valid, message): whether usable and detailed message
    """
    total = len(df_nwp)
    
    if total == 0:
        return False, "NWP rain data completely missing"
    
    # Check required columns
    required_cols = ['rain_mm', 'rain_label']
    prob_cols = ['rain_probability', 'P_rain']
    
    missing_cols = [c for c in required_cols if c not in df_nwp.columns]
    has_prob = any(c in df_nwp.columns for c in prob_cols)
    
    if missing_cols:
        return False, f"NWP missing required columns: {missing_cols}"
    
    if not has_prob:
        return False, f"NWP missing rain probability column (need one of {prob_cols})"
    
    # Check rain amount missing rate
    missing = df_nwp['rain_mm'].isna().sum()
    missing_rate = missing / total
    
    if missing_rate > threshold_missing:
        return False, f"NWP rain amount high missing rate: {missing_rate*100:.1f}% (threshold: {threshold_missing*100:.0f}%)"
    
    # Check abnormal values (rain amount 0-200 mm/h)
    rain_values = df_nwp['rain_mm'].dropna()
    if len(rain_values) > 0:
        abnormal = ((rain_values < 0) | (rain_values > 200)).sum()
        abnormal_rate = abnormal / len(rain_values)
        
        if abnormal_rate > 0.05:
            return False, f"NWP abnormal values too high: {abnormal_rate*100:.1f}%"
    
    return True, f"NWP rain forecast quality good (missing rate: {missing_rate*100:.1f}%)"


# =========================
# Load ML model
# =========================
def load_ml_models(model_path: str) -> Dict:
    """Load trained rain prediction model"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"ML model file not found: {model_path}")
    
    bundle = joblib.load(model_path)
    
    print(f"  ML model loaded successfully")
    print(f"    - Station: {bundle['station_id']}")
    print(f"    - Forecast horizon: {bundle['horizon']} hours")
    print(f"    - Rain threshold: {bundle['rain_thr']} mm/h")
    if bundle.get('heavy_thr'):
        print(f"    - Heavy rain threshold: {bundle['heavy_thr']} mm/h")
    
    return bundle


# =========================
# ML model prediction (fallback)
# =========================
def pure_ml_predict(bundle: Dict, issue_time: pd.Timestamp) -> pd.DataFrame:
    """
    Pure ML fallback prediction
    
    Note: This is a simplified version for demonstration.
    In production, you need complete feature engineering from observations.
    
    Args:
        bundle: model bundle
        issue_time: forecast issue time
    
    Returns:
        DataFrame with predictions
    """
    models_pop = bundle['models_pop']
    models_intensity = bundle['models_intensity']
    models_heavy = bundle.get('models_heavy')
    thresholds = bundle['thresholds_pop']
    heavy_thr = bundle.get('heavy_thr')
    feature_cols = bundle['feature_cols']
    
    print(f"\n Using simplified ML prediction")
    print(f" Production environment needs complete feature engineering")
    
    # Create dummy feature row (for demonstration)
    # In production, this should come from actual observation data
    feature_row = pd.DataFrame([[0] * len(feature_cols)], columns=feature_cols)
    
    predictions = []
    
    for h in range(1, HORIZON + 1):
        # PoP prediction
        p_pop = 0.0
        if models_pop.get(h) is not None:
            try:
                if hasattr(models_pop[h], 'predict_proba'):
                    p_pop = float(models_pop[h].predict_proba(feature_row)[0, 1])
            except:
                p_pop = 0.0
        
        # Heavy rain probability
        p_heavy = 0.0
        if heavy_thr is not None and models_heavy is not None:
            if models_heavy.get(h) is not None:
                try:
                    if hasattr(models_heavy[h], 'predict_proba'):
                        p_heavy = float(models_heavy[h].predict_proba(feature_row)[0, 1])
                        # Probability consistency: P(heavy) <= P(rain)
                        p_heavy = min(p_heavy, p_pop)
                except:
                    p_heavy = 0.0
        
        # Rain intensity prediction
        mu = 0.0
        if models_intensity.get(h) is not None:
            try:
                mu = float(models_intensity[h].predict(feature_row)[0])
            except:
                mu = 0.0
        
        # Expected rain amount
        rain_mm = p_pop * mu if mu > 0 else 0.0
        
        # Rain flag
        rain_flag = 0
        if thresholds.get(h) is not None:
            rain_flag = int(p_pop >= thresholds[h])
        
        # Rain level label
        if p_pop < 0.20:
            label = "No rain"
        else:
            if heavy_thr is not None and p_heavy >= 0.20:
                if heavy_thr <= 2.5:
                    label = "Moderate rain"
                else:
                    label = "Heavy rain"
            else:
                label = "Light rain"
        
        predictions.append({
            'time': issue_time + pd.Timedelta(hours=h),
            'rain_mm': rain_mm,
            'rain_probability': int(p_pop * 100),
            'rain_flag': rain_flag,
            'P_rain': p_pop,
            'P_moderate': p_heavy if heavy_thr and heavy_thr <= 2.5 else 0.0,
            'P_heavy': p_heavy if heavy_thr and heavy_thr > 2.5 else 0.0,
            'rain_label': label,
        })
    
    return pd.DataFrame(predictions)


# =========================
# Main production forecast
# =========================
def production_forecast(csv_nwp_future: str,
                       ml_model_path: str,
                       horizon_days: int = 7,
                       nwp_missing_threshold: float = 0.1) -> pd.DataFrame:
    """
    Production-grade rain forecasting system
    
    Strategy:
    1. Prefer NWP rain forecast
    2. Check NWP quality (missing rate, abnormal values)
    3. If NWP unusable → fallback to ML model
    4. Return forecast results + method used
    
    Returns:
        DataFrame: [time, rain_mm, rain_probability, rain_flag, P_rain, P_moderate, P_heavy, rain_label, forecast_method, confidence]
    """
    
    print("="*70)
    print("production-grade rain prediction system")
    print("="*70)
    
    horizon_hours = horizon_days * 24
    
    # 1. load NWP forecast
    print("\nloading NWP rain forecast...")
    try:
        df_nwp = pd.read_csv(csv_nwp_future)
        if 'time' in df_nwp.columns:
            df_nwp['time'] = pd.to_datetime(df_nwp['time'])
        print(f"NWP forecast length: {len(df_nwp)} hours")
    except Exception as e:
        print(f"cannot load NWP forecast: {e}")
        raise
    
    # 2. check NWP quality
    print("\nchecking NWP data quality...")
    is_nwp_valid, nwp_message = check_nwp_rain_quality(df_nwp, nwp_missing_threshold)
    print(f"  {nwp_message}")
    
    # 3. Decision: use NWP or fallback to ML
    if is_nwp_valid:
        print("\nDecision: Use NWP rain forecast")
        print(" Reason: NWP data quality is good")
        
        # Standardize column names
        df_result = df_nwp.copy()
        
        # Ensure probability column exists
        if 'P_rain' not in df_result.columns and 'rain_probability' in df_result.columns:
            df_result['P_rain'] = df_result['rain_probability'] / 100.0
        elif 'rain_probability' not in df_result.columns and 'P_rain' in df_result.columns:
            df_result['rain_probability'] = (df_result['P_rain'] * 100).astype(int)
        
        # Ensure rain flag exists
        if 'rain_flag' not in df_result.columns and 'P_rain' in df_result.columns:
            df_result['rain_flag'] = (df_result['P_rain'] >= 0.2).astype(int)
        
        # Ensure P_moderate and P_heavy exist
        if 'P_moderate' not in df_result.columns:
            df_result['P_moderate'] = 0.0
        if 'P_heavy' not in df_result.columns:
            df_result['P_heavy'] = 0.0
        
        # Fill missing values
        if df_result['rain_mm'].isna().any():
            n_missing = df_result['rain_mm'].isna().sum()
            print(f" fill {n_missing} missing rain amount values with linear interpolation")
            df_result['rain_mm'] = df_result['rain_mm'].interpolate(method='linear').fillna(0)
        
        df_result['forecast_method'] = 'NWP'
        df_result['confidence'] = 'high'
        # Keep only standard output columns
        output_cols = [
            'time', 'rain_mm', 'rain_probability', 'rain_flag',
            'P_rain', 'P_moderate', 'P_heavy', 'rain_label',
            'forecast_method', 'confidence'
        ]

        df_result = df_result[[c for c in output_cols if c in df_result.columns]]
        
    else:
        print("\nDecision: Fallback to Pure ML rain model")
        
        # Check ML model
        if not os.path.exists(ml_model_path):
            raise FileNotFoundError(
                f"Pure ML model not found: need {ml_model_path}"
            )
        
        # Load ML model
        print(f"\nloading ML model...")
        bundle = load_ml_models(ml_model_path)
        
        # Get issue time
        issue_time = df_nwp['time'].iloc[0] if 'time' in df_nwp.columns else pd.Timestamp.now()
        
        # ML prediction
        print(f"\nexecuting ML prediction...")
        df_result = pure_ml_predict(bundle, issue_time)
        
        df_result['forecast_method'] = 'Pure_ML_Fallback'
        df_result['confidence'] = 'medium'
    
    # 4. add forecast timestamp
    df_result['forecast_time'] = pd.Timestamp.now()
    
    # 5. limit to horizon hours
    df_result = df_result.head(horizon_hours)
    
    print(f"\nrediction completed")
    print(f"  Prediction length: {len(df_result)} hours")
    print(f"  Method used: {df_result['forecast_method'].iloc[0]}")
    print(f"  Confidence: {df_result['confidence'].iloc[0]}")
    
    return df_result


# =========================
# Hybrid forecast (partial NWP missing)
# =========================
def hybrid_forecast(csv_nwp_future: str, ml_model_path: str, horizon_days: int = 7) -> pd.DataFrame:
    """
    Hybrid rain forecast: decide per timestamp whether to use NWP or ML
    
    Use case: NWP has partial rain data missing
    """
    
    horizon_hours = horizon_days * 24
    
    df_nwp = pd.read_csv(csv_nwp_future)
    if 'time' in df_nwp.columns:
        df_nwp['time'] = pd.to_datetime(df_nwp['time'])
    
    df_result = df_nwp.copy()
    
    if 'rain_mm' not in df_result.columns:
        df_result['rain_mm'] = np.nan
    
    missing_mask = df_result['rain_mm'].isna()
    
    if missing_mask.sum() == 0:
        # Ensure required columns exist
        if 'P_rain' not in df_result.columns and 'rain_probability' in df_result.columns:
            df_result['P_rain'] = df_result['rain_probability'] / 100.0
        if 'rain_flag' not in df_result.columns:
            df_result['rain_flag'] = (df_result.get('P_rain', 0) >= 0.2).astype(int)
        if 'P_moderate' not in df_result.columns:
            df_result['P_moderate'] = 0.0
        if 'P_heavy' not in df_result.columns:
            df_result['P_heavy'] = 0.0
        
        df_result['forecast_method'] = 'NWP'
        df_result['confidence'] = 'high'
        return df_result.head(horizon_hours)
    
    print("Using Pure ML for missing timestamps")
    
    # Load ML model
    bundle = load_ml_models(ml_model_path)
    issue_time = df_nwp['time'].iloc[0] if 'time' in df_nwp.columns else pd.Timestamp.now()
    
    # ML prediction (as backup)
    ml_pred = pure_ml_predict(bundle, issue_time)
    
    # Hybrid: use NWP where available, ML where missing
    for col in ['rain_mm', 'rain_probability', 'rain_flag', 'P_rain', 
                'P_moderate', 'P_heavy', 'rain_label']:
        if col in ml_pred.columns:
            if col not in df_result.columns:
                df_result[col] = np.nan
            df_result.loc[missing_mask, col] = ml_pred.loc[missing_mask, col].values
    
    df_result.loc[missing_mask, 'forecast_method'] = 'Pure_ML_Fallback'
    df_result.loc[~missing_mask, 'forecast_method'] = 'NWP'
    
    df_result['confidence'] = 'high'
    df_result.loc[missing_mask, 'confidence'] = 'medium'
    
    return df_result.head(horizon_hours)


# =========================
# main
# =========================
def main():
    parser = argparse.ArgumentParser(description="Production-level rain prediction system")
    parser.add_argument("--csv_nwp_future", type=str, default="NWP_future_20004002.csv",
                       help="NWP future forecast file")
    parser.add_argument("--ml_model", type=str, default="./point_weights/rain_station20004002_h168_bundle.joblib",
                       help="ML model file path")
    parser.add_argument("--horizon_days", type=int, default=7)
    parser.add_argument("--output", type=str, default="forecast_rain_production.csv")
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "hybrid"],
                       help="Prediction mode: auto=auto select NWP/ML, hybrid=per-hour hybrid")
    parser.add_argument("--nwp_threshold", type=float, default=0.1,
                       help="NWP allowed maximum missing rate (0-1)")
    
    args = parser.parse_args()
    
    try:
        if args.mode == "auto":
            # Automatic mode: Determines whether to use NWP or ML
            df_forecast = production_forecast(
                args.csv_nwp_future,
                args.ml_model,
                args.horizon_days,
                args.nwp_threshold
            )
        else:
            # Hybrid mode: decide per timestamp whether to use NWP or ML
            df_forecast = hybrid_forecast(
                args.csv_nwp_future,
                args.ml_model,
                args.horizon_days
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
        
        if 'rain_label' in df_forecast.columns:
            label_counts = df_forecast['rain_label'].value_counts()
            print(f"\nRain level statistics:")
            for label, count in label_counts.items():
                print(f"  {label}: {count} hours ({count/len(df_forecast)*100:.1f}%)")
        
        if 'rain_mm' in df_forecast.columns:
            total_rain = df_forecast['rain_mm'].sum()
            rainy_hours = (df_forecast['rain_flag'] == 1).sum() if 'rain_flag' in df_forecast.columns else 0
            print(f"\nRain summary:")
            print(f"  Total rainfall: {total_rain:.1f} mm")
            print(f"  Rainy hours: {rainy_hours} hours ({rainy_hours/len(df_forecast)*100:.1f}%)")
        
        print(f"\nPrediction complete!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
