import type { WeatherForecast, WeatherData, ForecastDay, HourlyForecast } from '@/types/weather.types';

const API_CONFIG = {

  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api',
  endpoints: {
    current: '/weather/current',
    forecast: '/weather/forecast',
    hourly: '/weather/hourly',
  },

  openWeatherMap: {
    key: process.env.NEXT_PUBLIC_OPENWEATHER_API_KEY || '',
    baseURL: 'https:
  }
};

class WeatherService {

  async getCurrentWeather(city: string = 'Paris'): Promise<WeatherData> {
    try {
      const response = await fetch(
        `${API_CONFIG.baseURL}${API_CONFIG.endpoints.current}?city=${encodeURIComponent(city)}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          cache: 'no-store',
        }
      );

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformCurrentWeather(data);
    } catch (error) {
      console.error('Erreur lors de la récupération de la météo actuelle:', error);
      throw this.handleError(error);
    }
  }

  async getFullForecast(city: string = 'Paris'): Promise<WeatherForecast> {
    try {
      const response = await fetch(
        `${API_CONFIG.baseURL}${API_CONFIG.endpoints.forecast}?city=${encodeURIComponent(city)}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          cache: 'no-store',
        }
      );

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformForecastData(data);
    } catch (error) {
      console.error('Erreur lors de la récupération des prévisions:', error);
      throw this.handleError(error);
    }
  }

  async getHourlyForecast(city: string = 'Paris', hours: number = 24): Promise<HourlyForecast[]> {
    try {
      const response = await fetch(
        `${API_CONFIG.baseURL}${API_CONFIG.endpoints.hourly}?city=${encodeURIComponent(city)}&hours=${hours}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          cache: 'no-store',
        }
      );

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformHourlyData(data);
    } catch (error) {
      console.error('Erreur lors de la récupération des prévisions horaires:', error);
      throw this.handleError(error);
    }
  }

  async getDemoCurrentWeather(city: string = 'Paris'): Promise<WeatherData> {
    const apiKey = API_CONFIG.openWeatherMap.key;
    if (!apiKey) {
      throw new Error('Clé API OpenWeatherMap manquante');
    }

    try {
      const response = await fetch(
        `${API_CONFIG.openWeatherMap.baseURL}/weather?q=${encodeURIComponent(city)}&appid=${apiKey}&units=metric&lang=fr`
      );

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }

      const data = await response.json();

      return {
        location: data.name,
        country: data.sys.country,
        temperature: Math.round(data.main.temp),
        feelsLike: Math.round(data.main.feels_like),
        humidity: data.main.humidity,
        pressure: data.main.pressure,
        windSpeed: data.wind.speed,
        windDirection: data.wind.deg,
        description: data.weather[0].description,
        icon: data.weather[0].icon,
        timestamp: new Date(),
        sunrise: new Date(data.sys.sunrise * 1000),
        sunset: new Date(data.sys.sunset * 1000),
      };
    } catch (error) {
      console.error('Erreur DEMO OpenWeatherMap:', error);
      throw this.handleError(error);
    }
  }

  async getDemoFullForecast(city: string = 'Paris'): Promise<WeatherForecast> {
    const apiKey = API_CONFIG.openWeatherMap.key;
    if (!apiKey) {
      throw new Error('Clé API OpenWeatherMap manquante');
    }

    try {

      const [currentResponse, forecastResponse] = await Promise.all([
        fetch(`${API_CONFIG.openWeatherMap.baseURL}/weather?q=${encodeURIComponent(city)}&appid=${apiKey}&units=metric&lang=fr`),
        fetch(`${API_CONFIG.openWeatherMap.baseURL}/forecast?q=${encodeURIComponent(city)}&appid=${apiKey}&units=metric&lang=fr`)
      ]);

      if (!currentResponse.ok || !forecastResponse.ok) {
        throw new Error('Erreur lors de la récupération des données');
      }

      const currentData = await currentResponse.json();
      const forecastData = await forecastResponse.json();

      const current: WeatherData = {
        location: currentData.name,
        country: currentData.sys.country,
        temperature: Math.round(currentData.main.temp),
        feelsLike: Math.round(currentData.main.feels_like),
        humidity: currentData.main.humidity,
        pressure: currentData.main.pressure,
        windSpeed: currentData.wind.speed,
        windDirection: currentData.wind.deg,
        description: currentData.weather[0].description,
        icon: currentData.weather[0].icon,
        timestamp: new Date(),
        sunrise: new Date(currentData.sys.sunrise * 1000),
        sunset: new Date(currentData.sys.sunset * 1000),
      };

      const hourly: HourlyForecast[] = forecastData.list.slice(0, 8).map((item: any) => ({
        time: new Date(item.dt * 1000),
        temperature: Math.round(item.main.temp),
        feelsLike: Math.round(item.main.feels_like),
        precipitation: (item.rain?.['3h'] || 0) + (item.snow?.['3h'] || 0),
        humidity: item.main.humidity,
        windSpeed: item.wind.speed,
        description: item.weather[0].description,
        icon: item.weather[0].icon,
      }));

      const dailyMap = new Map<string, any[]>();
      forecastData.list.forEach((item: any) => {
        const date = new Date(item.dt * 1000).toDateString();
        if (!dailyMap.has(date)) {
          dailyMap.set(date, []);
        }
        dailyMap.get(date)?.push(item);
      });

      const daily: ForecastDay[] = Array.from(dailyMap.entries()).slice(0, 7).map(([dateStr, items]) => {
        const temps = items.map(item => item.main.temp);
        const humidities = items.map(item => item.main.humidity);
        const precipitations = items.map(item => (item.rain?.['3h'] || 0) + (item.snow?.['3h'] || 0));
        const winds = items.map(item => item.wind.speed);

        return {
          date: new Date(dateStr),
          tempMin: Math.round(Math.min(...temps)),
          tempMax: Math.round(Math.max(...temps)),
          humidity: Math.round(humidities.reduce((a, b) => a + b, 0) / humidities.length),
          precipitation: Math.round(precipitations.reduce((a, b) => a + b, 0)),
          windSpeed: Math.round(winds.reduce((a, b) => a + b, 0) / winds.length),
          description: items[Math.floor(items.length / 2)].weather[0].description,
          icon: items[Math.floor(items.length / 2)].weather[0].icon,
        };
      });

      return { current, hourly, daily };
    } catch (error) {
      console.error('Erreur DEMO OpenWeatherMap:', error);
      throw this.handleError(error);
    }
  }

  private transformCurrentWeather(data: any): WeatherData {

    return {
      location: data.location || data.city,
      country: data.country || '',
      temperature: data.temperature || data.temp,
      feelsLike: data.feelsLike || data.feels_like,
      humidity: data.humidity,
      pressure: data.pressure,
      windSpeed: data.windSpeed || data.wind_speed,
      windDirection: data.windDirection || data.wind_direction || 0,
      description: data.description || '',
      icon: data.icon || '01d',
      timestamp: new Date(data.timestamp || Date.now()),
      sunrise: data.sunrise ? new Date(data.sunrise) : undefined,
      sunset: data.sunset ? new Date(data.sunset) : undefined,
    };
  }

  private transformForecastData(data: any): WeatherForecast {

    return {
      current: this.transformCurrentWeather(data.current),
      hourly: data.hourly?.map(this.transformHourlyData) || [],
      daily: data.daily?.map(this.transformDailyData) || [],
    };
  }

  private transformHourlyData(item: any): HourlyForecast {
    return {
      time: new Date(item.time || item.timestamp),
      temperature: item.temperature || item.temp,
      feelsLike: item.feelsLike || item.feels_like,
      precipitation: item.precipitation || 0,
      humidity: item.humidity,
      windSpeed: item.windSpeed || item.wind_speed,
      description: item.description,
      icon: item.icon,
    };
  }

  private transformDailyData(item: any): ForecastDay {
    return {
      date: new Date(item.date || item.timestamp),
      tempMin: item.tempMin || item.temp_min,
      tempMax: item.tempMax || item.temp_max,
      humidity: item.humidity,
      precipitation: item.precipitation || 0,
      windSpeed: item.windSpeed || item.wind_speed,
      description: item.description,
      icon: item.icon,
    };
  }

  private handleError(error: unknown): Error {
    if (error instanceof Error) {
      return error;
    }
    return new Error('Une erreur inconnue est survenue');
  }
}

export const weatherService = new WeatherService();
