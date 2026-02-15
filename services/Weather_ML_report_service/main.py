import pandas as pd
from db_handler import get_weather_data, save_predictions
from ml_engine import run_ml_pipeline
from viz_engine import generate_global_maps, generate_station_charts
from notifier import send_personalized_email

def main():
    customers = pd.read_csv('customers.csv')
    df_brut = get_weather_data()
    
    df_forecast = run_ml_pipeline(df_brut)
    save_predictions(df_forecast)
    
    global_maps = generate_global_maps(df_forecast)

    for _, c in customers.iterrows():
        station_data_full = df_forecast[df_forecast['station'] == c['station_name']]
        
        charts = generate_station_charts(df_forecast, c['station_name'])
        
        send_personalized_email(
            email=c['email'], 
            name=c['name'], 
            station=c['station_name'], 
            stats_full=station_data_full, 
            global_maps=global_maps, 
            station_charts=charts
        )

if __name__ == "__main__":
    main()