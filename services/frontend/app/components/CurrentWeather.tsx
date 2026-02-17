'use client';

import { motion } from 'framer-motion';
import { WiHumidity, WiBarometer, WiStrongWind, WiSunrise, WiSunset } from 'react-icons/wi';
import type { WeatherData } from '@/types/weather.types';
import {
  formatTemperature,
  formatWindSpeed,
  formatHumidity,
  formatPressure,
  formatTime,
  degreesToCardinal,
  getWeatherIcon,
  getTemperatureColor,
  isNightTime,
} from '@/utils/weather.utils';

interface CurrentWeatherProps {
  data: WeatherData;
  className?: string;
}

export function CurrentWeather({ data, className = '' }: CurrentWeatherProps) {
  const isNight = isNightTime(data.sunrise, data.sunset);
  const tempColor = getTemperatureColor(data.temperature);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`rounded-2xl bg-white shadow-xl p-6 md:p-8 ${className}`}
    >

      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-3xl md:text-4xl font-bold text-gray-800">
            {data.location}
          </h2>
          <p className="text-gray-500 mt-1">
            {data.country} • {new Date(data.timestamp).toLocaleDateString('fr-FR', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}
          </p>
        </div>

        <motion.img
          src={getWeatherIcon(data.icon)}
          alt={data.description}
          className="w-20 h-20 md:w-24 md:h-24"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring' }}
        />
      </div>

      <div className="mb-6">
        <div className="flex items-baseline gap-2">
          <motion.span
            className={`text-6xl md:text-7xl font-bold ${tempColor}`}
            initial={{ scale: 0.5 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, type: 'spring' }}
          >
            {formatTemperature(data.temperature)}
          </motion.span>
          <span className="text-2xl text-gray-400">
            Ressenti {formatTemperature(data.feelsLike)}
          </span>
        </div>
        <p className="text-xl text-gray-600 mt-2 capitalize">
          {data.description}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <motion.div
          className="flex items-center gap-3 p-4 rounded-xl bg-blue-50"
          whileHover={{ scale: 1.05 }}
          transition={{ type: 'spring', stiffness: 300 }}
        >
          <WiHumidity className="text-4xl text-blue-500" />
          <div>
            <p className="text-sm text-gray-600">Humidité</p>
            <p className="text-lg font-semibold text-gray-800">
              {formatHumidity(data.humidity)}
            </p>
          </div>
        </motion.div>

        <motion.div
          className="flex items-center gap-3 p-4 rounded-xl bg-purple-50"
          whileHover={{ scale: 1.05 }}
          transition={{ type: 'spring', stiffness: 300 }}
        >
          <WiBarometer className="text-4xl text-purple-500" />
          <div>
            <p className="text-sm text-gray-600">Pression</p>
            <p className="text-lg font-semibold text-gray-800">
              {formatPressure(data.pressure)}
            </p>
          </div>
        </motion.div>

        <motion.div
          className="flex items-center gap-3 p-4 rounded-xl bg-teal-50"
          whileHover={{ scale: 1.05 }}
          transition={{ type: 'spring', stiffness: 300 }}
        >
          <WiStrongWind className="text-4xl text-teal-500" />
          <div>
            <p className="text-sm text-gray-600">Vent</p>
            <p className="text-lg font-semibold text-gray-800">
              {formatWindSpeed(data.windSpeed)}
            </p>
            <p className="text-xs text-gray-500">
              {degreesToCardinal(data.windDirection)}
            </p>
          </div>
        </motion.div>

        <motion.div
          className="flex items-center gap-3 p-4 rounded-xl bg-amber-50"
          whileHover={{ scale: 1.05 }}
          transition={{ type: 'spring', stiffness: 300 }}
        >
          {isNight ? (
            <>
              <WiSunrise className="text-4xl text-amber-500" />
              <div>
                <p className="text-sm text-gray-600">Lever</p>
                <p className="text-lg font-semibold text-gray-800">
                  {data.sunrise ? formatTime(data.sunrise) : '--:--'}
                </p>
              </div>
            </>
          ) : (
            <>
              <WiSunset className="text-4xl text-orange-500" />
              <div>
                <p className="text-sm text-gray-600">Coucher</p>
                <p className="text-lg font-semibold text-gray-800">
                  {data.sunset ? formatTime(data.sunset) : '--:--'}
                </p>
              </div>
            </>
          )}
        </motion.div>
      </div>

      <div className="mt-6 text-center">
        <p className="text-xs text-gray-400">
          Dernière mise à jour: {formatTime(data.timestamp)}
        </p>
      </div>
    </motion.div>
  );
}
