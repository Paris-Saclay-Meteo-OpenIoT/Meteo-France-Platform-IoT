'use client';

import { motion } from 'framer-motion';
import { WiRaindrop, WiStrongWind } from 'react-icons/wi';
import type { ForecastDay } from '@/types/weather.types';
import {
  formatTemperature,
  formatDate,
  getWeatherIcon,
  formatWindSpeed,
  formatHumidity,
  getTemperatureColor,
} from '@/utils/weather.utils';

interface DailyForecastProps {
  forecasts: ForecastDay[];
  className?: string;
}

export function DailyForecast({ forecasts, className = '' }: DailyForecastProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className={`rounded-2xl bg-white shadow-xl p-6 ${className}`}
    >
      <h3 className="text-2xl font-bold text-gray-800 mb-6">
        Prévisions sur 7 jours
      </h3>

      <div className="space-y-3">
        {forecasts.map((forecast, index) => (
          <motion.div
            key={forecast.date.toISOString()}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.02, backgroundColor: '#f9fafb' }}
            className="flex items-center justify-between p-4 rounded-xl border border-gray-100 hover:border-gray-200 transition-all cursor-pointer"
          >

            <div className="flex-1 min-w-[120px]">
              <p className="font-semibold text-gray-800">
                {formatDate(forecast.date, 'short')}
              </p>
              <p className="text-sm text-gray-500 capitalize">
                {forecast.description}
              </p>
            </div>

            <div className="flex-shrink-0 mx-4">
              <img
                src={getWeatherIcon(forecast.icon)}
                alt={forecast.description}
                className="w-12 h-12"
              />
            </div>

            <div className="flex items-center gap-4 flex-1 justify-center">
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Max</p>
                <p className={`text-xl font-bold ${getTemperatureColor(forecast.tempMax)}`}>
                  {formatTemperature(forecast.tempMax)}
                </p>
              </div>
              <div className="w-16 h-1 bg-gradient-to-r from-blue-400 to-red-400 rounded-full" />
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Min</p>
                <p className={`text-xl font-bold ${getTemperatureColor(forecast.tempMin)}`}>
                  {formatTemperature(forecast.tempMin)}
                </p>
              </div>
            </div>

            <div className="hidden md:flex items-center gap-6 flex-1 justify-end">

              <div className="flex items-center gap-2">
                <WiRaindrop className="text-2xl text-blue-500" />
                <span className="text-sm text-gray-600">
                  {forecast.precipitation > 0 ? `${forecast.precipitation}mm` : '-'}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <WiStrongWind className="text-2xl text-teal-500" />
                <span className="text-sm text-gray-600">
                  {formatWindSpeed(forecast.windSpeed)}
                </span>
              </div>

              <div className="text-sm text-gray-600 min-w-[50px] text-right">
                {formatHumidity(forecast.humidity)}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
