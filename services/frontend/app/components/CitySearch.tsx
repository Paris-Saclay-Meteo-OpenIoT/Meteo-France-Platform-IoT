'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { FaSearch, FaMapMarkerAlt } from 'react-icons/fa';

interface CitySearchProps {
  onSearch: (city: string) => void;
  initialCity?: string;
  isLoading?: boolean;
}

const POPULAR_CITIES = [
  'Paris',
  'Marseille',
  'Lyon',
  'Toulouse',
  'Nice',
  'Bordeaux',
  'Lille',
  'Strasbourg',
];

export function CitySearch({ onSearch, initialCity = '', isLoading = false }: CitySearchProps) {
  const [city, setCity] = useState(initialCity);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (city.trim()) {
      onSearch(city.trim());
    }
  };

  const handleCityClick = (selectedCity: string) => {
    setCity(selectedCity);
    onSearch(selectedCity);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full"
    >

      <form onSubmit={handleSubmit} className="relative mb-4">
        <div className="relative">
          <FaMapMarkerAlt className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-xl" />
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Rechercher une ville..."
            disabled={isLoading}
            className="w-full pl-12 pr-12 py-4 text-lg rounded-xl border-2 border-gray-200 focus:border-blue-500 focus:outline-none transition-colors disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <motion.button
            type="submit"
            disabled={isLoading || !city.trim()}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            <FaSearch className="text-lg" />
          </motion.button>
        </div>
      </form>

      <div>
        <p className="text-sm text-gray-600 mb-3 font-medium">Villes populaires :</p>
        <div className="flex flex-wrap gap-2">
          {POPULAR_CITIES.map((popularCity) => (
            <motion.button
              key={popularCity}
              onClick={() => handleCityClick(popularCity)}
              disabled={isLoading}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                city === popularCity
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {popularCity}
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
