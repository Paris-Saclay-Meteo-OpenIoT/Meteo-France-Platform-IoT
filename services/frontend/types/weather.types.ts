export interface WeatherData {
  location: string;
  country: string;
  temperature: number;
  feelsLike: number;
  humidity: number;
  pressure: number;
  windSpeed: number;
  windDirection: number;
  description: string;
  icon: string;
  timestamp: Date;
  sunrise?: Date;
  sunset?: Date;
}

export interface ForecastDay {
  date: Date;
  tempMin: number;
  tempMax: number;
  humidity: number;
  precipitation: number;
  windSpeed: number;
  description: string;
  icon: string;
}

export interface HourlyForecast {
  time: Date;
  temperature: number;
  feelsLike: number;
  precipitation: number;
  humidity: number;
  windSpeed: number;
  description: string;
  icon: string;
}

export interface WeatherForecast {
  current: WeatherData;
  hourly: HourlyForecast[];
  daily: ForecastDay[];
}

export interface WeatherError {
  message: string;
  code?: string;
  timestamp: Date;
}

export type WeatherLoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface WeatherState {
  data: WeatherForecast | null;
  loading: WeatherLoadingState;
  error: WeatherError | null;
  lastUpdated: Date | null;
}
