import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta

def run_ml_pipeline(df):
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna().copy()
    le = LabelEncoder()
    df['SID'] = le.fit_transform(df['nom_usuel'])
    coords_map = df[['nom_usuel', 'lat', 'lon']].drop_duplicates().set_index('nom_usuel')
    features = ['SID', 't', 'u', 'ff']
    stations = df['nom_usuel'].unique()
    last_run_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    all_rows = []
    for target_col in ['t', 'ff', 'rr1']:
        y = np.array([df[target_col].shift(-i).values for i in range(1, 25)]).T
        valid_idx = ~np.isnan(y).any(axis=1)
        X_train = df[valid_idx][features]
        y_train = y[valid_idx]
        model = RandomForestRegressor(n_estimators=50, n_jobs=-1, random_state=42)
        model.fit(X_train, y_train)
        for station in stations:
            last_data = df[df['nom_usuel'] == station].sort_values('date').iloc[-1:]
            preds = model.predict(last_data[features])[0]
            for i, val in enumerate(preds):
                forecast_time = last_run_time + timedelta(hours=i+1)
                found = False
                for row in all_rows:
                    if row['station'] == station and row['forecast_time'] == forecast_time:
                        row[f'{target_col.lower()}_pred'] = round(val, 2)
                        found = True
                        break
                if not found:
                    all_rows.append({
                        'station': station,
                        'forecast_time': forecast_time,
                        'lat': coords_map.loc[station, 'lat'], 
                        'lon': coords_map.loc[station, 'lon'], 
                        f'{target_col.lower()}_pred': round(val, 2)
                    })
    return pd.DataFrame(all_rows)