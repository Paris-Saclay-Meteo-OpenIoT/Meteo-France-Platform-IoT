'use client';

import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import type { HourlyForecast } from '@/types/weather.types';
import { formatTemperature, formatTime } from '@/utils/weather.utils';

interface HourlyForecastChartProps {
  forecasts: HourlyForecast[];
  className?: string;
}

export function HourlyForecastChart({ forecasts, className = '' }: HourlyForecastChartProps) {

  const chartData = forecasts.map(forecast => ({
    time: formatTime(forecast.time),
    temperature: forecast.temperature,
    feelsLike: forecast.feelsLike,
    humidity: forecast.humidity,
    precipitation: forecast.precipitation,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-200">
          <p className="font-semibold text-gray-800 mb-2">{payload[0].payload.time}</p>
          <div className="space-y-1">
            <p className="text-sm">
              <span className="text-red-500 font-semibold">Température:</span>{' '}
              {formatTemperature(payload[0].value)}
            </p>
            {payload[1] && (
              <p className="text-sm">
                <span className="text-orange-500 font-semibold">Ressenti:</span>{' '}
                {formatTemperature(payload[1].value)}
              </p>
            )}
            <p className="text-sm">
              <span className="text-blue-500 font-semibold">Humidité:</span>{' '}
              {payload[0].payload.humidity}%
            </p>
            {payload[0].payload.precipitation > 0 && (
              <p className="text-sm">
                <span className="text-cyan-500 font-semibold">Précipitations:</span>{' '}
                {payload[0].payload.precipitation.toFixed(1)}mm
              </p>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className={`rounded-2xl bg-white shadow-xl p-6 ${className}`}
    >
      <h3 className="text-2xl font-bold text-gray-800 mb-6">
        Prévisions horaires (24h)
      </h3>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorFeels" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.6}/>
                <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="time"
              stroke="#9ca3af"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              stroke="#9ca3af"
              tick={{ fontSize: 12 }}
              label={{ value: 'Température (°C)', angle: -90, position: 'insideLeft', style: { fill: '#9ca3af' } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="temperature"
              stroke="#ef4444"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#colorTemp)"
              name="Température"
            />
            <Area
              type="monotone"
              dataKey="feelsLike"
              stroke="#f97316"
              strokeWidth={2}
              strokeDasharray="5 5"
              fillOpacity={1}
              fill="url(#colorFeels)"
              name="Ressenti"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex justify-center gap-6 mt-4">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded" />
          <span className="text-sm text-gray-600">Température</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-orange-500 border-2 border-orange-500" style={{ borderStyle: 'dashed' }} />
          <span className="text-sm text-gray-600">Ressenti</span>
        </div>
      </div>
    </motion.div>
  );
}
