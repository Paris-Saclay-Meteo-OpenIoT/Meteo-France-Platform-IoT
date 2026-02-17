'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { FaSync, FaClock } from 'react-icons/fa';
import { useWeather } from '@/hooks/useWeather';
import { CitySearch } from '@/app/components/weather/CitySearch';
import { CurrentWeather } from '@/app/components/weather/CurrentWeather';
import { DailyForecast } from '@/app/components/weather/DailyForecast';
import { HourlyForecastChart } from '@/app/components/weather/HourlyForecastChart';
import { WeatherLoading, WeatherError } from '@/app/components/weather/WeatherStates';
import { formatTime } from '@/utils/weather.utils';

export default function Forecast() {
  const [selectedCity, setSelectedCity] = useState('Paris');

  const {
    data,
    loading,
    error,
    lastUpdated,
    isLoading,
    isError,
    isSuccess,
    changeCity,
    refresh,
  } = useWeather({
    city: selectedCity,
    autoFetch: true,
    refreshInterval: 5 * 60 * 1000,
    useDemo: true,
  });

  const handleCitySearch = (city) => {
    setSelectedCity(city);
    changeCity(city);
  };

  const handleRefresh = () => {
    refresh();
  };

  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-blue-50 via-cyan-50 to-teal-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-blue-700">
                Prévisions Météo
              </h1>
              <p className="text-gray-600 mt-1">
                Consultez les prévisions météorologiques en temps réel
              </p>
            </div>

            {isSuccess && (
              <div className="flex items-center gap-4">
                {lastUpdated && (
                  <div className="hidden md:flex items-center gap-2 text-sm text-gray-500">
                    <FaClock />
                    <span>Mise à jour: {formatTime(lastUpdated)}</span>
                  </div>
                )}
                <motion.button
                  onClick={handleRefresh}
                  disabled={isLoading}
                  whileHover={{ scale: 1.05, rotate: 180 }}
                  whileTap={{ scale: 0.95 }}
                  className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                  title="Rafraîchir"
                >
                  <FaSync className={isLoading ? 'animate-spin' : ''} />
                </motion.button>
              </div>
            )}
          </div>

          <CitySearch
            onSearch={handleCitySearch}
            initialCity={selectedCity}
            isLoading={isLoading}
          />
        </div>

        {isLoading && <WeatherLoading />}

        {isError && (
          <WeatherError
            message={error?.message || 'Impossible de récupérer les données météo'}
            onRetry={handleRefresh}
          />
        )}

        {isSuccess && data && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >

            <CurrentWeather data={data.current} />

            <div className="grid grid-cols-1 gap-6">

              {data.hourly && data.hourly.length > 0 && (
                <HourlyForecastChart forecasts={data.hourly} />
              )}

              {data.daily && data.daily.length > 0 && (
                <DailyForecast forecasts={data.daily} />
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
