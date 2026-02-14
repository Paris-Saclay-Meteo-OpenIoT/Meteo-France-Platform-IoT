import { useState, useEffect, useCallback } from 'react';
import { weatherService } from '@/services/weather.service';
import type {
  WeatherForecast,
  WeatherState,
  WeatherError,
  WeatherLoadingState
} from '@/types/weather.types';

interface UseWeatherOptions {
  city?: string;
  autoFetch?: boolean;
  refreshInterval?: number;
  useDemo?: boolean;
}

export function useWeather(options: UseWeatherOptions = ) {
  const {
    city = 'Paris',
    autoFetch = true,
    refreshInterval,
    useDemo = true,
  } = options;

  const [state, setState] = useState<WeatherState>({
    data: null,
    loading: 'idle',
    error: null,
    lastUpdated: null,
  });

  const fetchWeather = useCallback(async (targetCity?: string) => {
    const cityToFetch = targetCity || city;

    setState(prev => ({
      ...prev,
      loading: 'loading',
      error: null,
    }));

    try {

      const data = useDemo
        ? await weatherService.getDemoFullForecast(cityToFetch)
        : await weatherService.getFullForecast(cityToFetch);

      setState({
        data,
        loading: 'success',
        error: null,
        lastUpdated: new Date(),
      });
    } catch (error) {
      const weatherError: WeatherError = {
        message: error instanceof Error ? error.message : 'Erreur inconnue',
        code: 'FETCH_ERROR',
        timestamp: new Date(),
      };

      setState({
        data: null,
        loading: 'error',
        error: weatherError,
        lastUpdated: null,
      });
    }
  }, [city, useDemo]);

  const refresh = useCallback(() => {
    fetchWeather();
  }, [fetchWeather]);

  const changeCity = useCallback((newCity: string) => {
    fetchWeather(newCity);
  }, [fetchWeather]);

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: 'idle',
      error: null,
      lastUpdated: null,
    });
  }, []);

  useEffect(() => {
    if (autoFetch) {
      fetchWeather();
    }
  }, [autoFetch, fetchWeather]);

  useEffect(() => {
    if (!refreshInterval || refreshInterval <= 0) return;

    const intervalId = setInterval(() => {
      if (state.loading !== 'loading') {
        fetchWeather();
      }
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [refreshInterval, fetchWeather, state.loading]);

  return {

    data: state.data,
    loading: state.loading,
    error: state.error,
    lastUpdated: state.lastUpdated,

    isLoading: state.loading === 'loading',
    isError: state.loading === 'error',
    isSuccess: state.loading === 'success',
    isIdle: state.loading === 'idle',

    fetch: fetchWeather,
    refresh,
    changeCity,
    reset,
  };
}

export function useCurrentWeather(city: string = 'Paris', useDemo: boolean = true) {
  const [temperature, setTemperature] = useState<number | null>(null);
  const [description, setDescription] = useState<string>('');
  const [loading, setLoading] = useState<WeatherLoadingState>('idle');
  const [error, setError] = useState<string | null>(null);

  const fetchCurrent = useCallback(async () => {
    setLoading('loading');
    setError(null);

    try {
      const data = useDemo
        ? await weatherService.getDemoCurrentWeather(city)
        : await weatherService.getCurrentWeather(city);

      setTemperature(data.temperature);
      setDescription(data.description);
      setLoading('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
      setLoading('error');
    }
  }, [city, useDemo]);

  useEffect(() => {
    fetchCurrent();
  }, [fetchCurrent]);

  return {
    temperature,
    description,
    loading,
    error,
    isLoading: loading === 'loading',
    isError: loading === 'error',
    refresh: fetchCurrent,
  };
}
