'use client';

import { motion } from 'framer-motion';
import { WiDaySunny, WiCloud, WiRain } from 'react-icons/wi';

export function WeatherLoading({ message = 'Chargement des données météo...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
      <div className="relative">

        <motion.div
          animate={{
            rotate: 360,
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: 'linear',
          }}
        >
          <WiDaySunny className="text-8xl text-yellow-400" />
        </motion.div>

        <motion.div
          className="absolute top-0 left-0"
          animate={{
            x: [0, 20, 0],
            opacity: [0.3, 1, 0.3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        >
          <WiCloud className="text-6xl text-gray-300" />
        </motion.div>

        <motion.div
          className="absolute top-0 right-0"
          animate={{
            y: [0, 10, 0],
            opacity: [0.3, 1, 0.3],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 0.5,
          }}
        >
          <WiRain className="text-5xl text-blue-400" />
        </motion.div>
      </div>

      <motion.p
        className="mt-8 text-lg text-gray-600 font-medium"
        animate={{
          opacity: [0.5, 1, 0.5],
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        {message}
      </motion.p>

      <div className="w-64 h-2 bg-gray-200 rounded-full mt-4 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-400"
          animate={{
            x: ['-100%', '100%'],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </div>
    </div>
  );
}

interface WeatherErrorProps {
  message: string;
  onRetry?: () => void;
}

export function WeatherError({ message, onRetry }: WeatherErrorProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center justify-center min-h-[400px] p-8"
    >

      <motion.div
        animate={{
          rotate: [0, -10, 10, -10, 0],
        }}
        transition={{
          duration: 0.5,
          repeat: 3,
        }}
        className="mb-6"
      >
        <svg
          className="w-24 h-24 text-red-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </motion.div>

      <h3 className="text-2xl font-bold text-gray-800 mb-2">
        Oups ! Une erreur est survenue
      </h3>
      <p className="text-gray-600 text-center max-w-md mb-6">
        {message}
      </p>

      {onRetry && (
        <motion.button
          onClick={onRetry}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="px-6 py-3 bg-blue-500 text-white rounded-lg font-semibold shadow-lg hover:bg-blue-600 transition-colors"
        >
          Réessayer
        </motion.button>
      )}

      <div className="mt-8 text-sm text-gray-500 text-center max-w-md">
        <p className="mb-2">Vérifiez que :</p>
        <ul className="space-y-1">
          <li>• Votre connexion internet fonctionne</li>
          <li>• Le serveur backend est accessible</li>
          <li>• La ville recherchée existe</li>
        </ul>
      </div>
    </motion.div>
  );
}

export function WeatherEmpty({ onSearch }: { onSearch?: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[400px] p-8"
    >
      <WiCloud className="text-9xl text-gray-300 mb-6" />
      <h3 className="text-2xl font-bold text-gray-800 mb-2">
        Aucune donnée météo
      </h3>
      <p className="text-gray-600 text-center max-w-md mb-6">
        Recherchez une ville pour voir les prévisions météorologiques
      </p>
      {onSearch && (
        <motion.button
          onClick={onSearch}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="px-6 py-3 bg-blue-500 text-white rounded-lg font-semibold shadow-lg hover:bg-blue-600 transition-colors"
        >
          Rechercher
        </motion.button>
      )}
    </motion.div>
  );
}
