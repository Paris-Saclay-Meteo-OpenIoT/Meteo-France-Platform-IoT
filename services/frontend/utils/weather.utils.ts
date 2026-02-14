export function formatTemperature(temp: number, unit: 'C' | 'F' = 'C'): string {
  return `${Math.round(temp)}°${unit}`;
}

export function formatWindSpeed(speed: number, unit: 'kmh' | 'ms' = 'kmh'): string {
  const value = unit === 'kmh' ? speed * 3.6 : speed;
  return `${Math.round(value)} ${unit === 'kmh' ? 'km/h' : 'm/s'}`;
}

export function degreesToCardinal(degrees: number): string {
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO'];
  const index = Math.round(((degrees % 360) / 22.5));
  return directions[index % 16];
}

export function formatHumidity(humidity: number): string {
  return `${Math.round(humidity)}%`;
}

export function formatPressure(pressure: number): string {
  return `${Math.round(pressure)} hPa`;
}

export function formatPrecipitation(mm: number): string {
  return `${mm.toFixed(1)} mm`;
}

export function getWeatherIcon(iconCode: string): string {
  return `https:
}

export function getWeatherEmoji(description: string): string {
  const desc = description.toLowerCase();

  if (desc.includes('ensoleillé') || desc.includes('clear')) return '☀️';
  if (desc.includes('nuageux') || desc.includes('cloud')) return '☁️';
  if (desc.includes('pluie') || desc.includes('rain')) return '🌧️';
  if (desc.includes('orage') || desc.includes('thunder')) return '⛈️';
  if (desc.includes('neige') || desc.includes('snow')) return '🌨️';
  if (desc.includes('brouillard') || desc.includes('fog') || desc.includes('mist')) return '🌫️';
  if (desc.includes('vent') || desc.includes('wind')) return '💨';

  return '🌤️';
}

export function formatDate(date: Date, format: 'short' | 'long' | 'time' = 'short'): string {
  const options: Intl.DateTimeFormatOptions =
    format === 'short' ? { weekday: 'short', day: 'numeric', month: 'short' } :
    format === 'long' ? { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' } :
    { hour: '2-digit', minute: '2-digit' };

  return new Intl.DateTimeFormat('fr-FR', options).format(date);
}

export function formatTime(date: Date): string {
  return new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

export function getTemperatureColor(temp: number): string {
  if (temp < 0) return 'text-blue-600';
  if (temp < 10) return 'text-blue-400';
  if (temp < 20) return 'text-green-500';
  if (temp < 25) return 'text-yellow-500';
  if (temp < 30) return 'text-orange-500';
  return 'text-red-500';
}

export function getWeatherBackground(description: string, isNight: boolean = false): string {
  const desc = description.toLowerCase();

  if (isNight) {
    return 'bg-gradient-to-br from-indigo-900 via-purple-900 to-blue-900';
  }

  if (desc.includes('ensoleillé') || desc.includes('clear')) {
    return 'bg-gradient-to-br from-blue-400 via-blue-300 to-cyan-200';
  }
  if (desc.includes('nuageux') || desc.includes('cloud')) {
    return 'bg-gradient-to-br from-gray-400 via-gray-300 to-blue-200';
  }
  if (desc.includes('pluie') || desc.includes('rain')) {
    return 'bg-gradient-to-br from-gray-600 via-gray-500 to-blue-400';
  }
  if (desc.includes('orage') || desc.includes('thunder')) {
    return 'bg-gradient-to-br from-gray-800 via-purple-800 to-indigo-700';
  }
  if (desc.includes('neige') || desc.includes('snow')) {
    return 'bg-gradient-to-br from-gray-200 via-blue-100 to-white';
  }

  return 'bg-gradient-to-br from-blue-500 via-cyan-400 to-teal-300';
}

export function isNightTime(sunrise?: Date, sunset?: Date): boolean {
  if (!sunrise || !sunset) {
    const hour = new Date().getHours();
    return hour < 6 || hour > 20;
  }

  const now = new Date();
  return now < sunrise || now > sunset;
}

export function calculateUVIndex(description: string): number {
  const hour = new Date().getHours();

  if (hour < 6 || hour > 20) return 0;

  if (description.includes('nuageux') || description.includes('pluie')) {
    return Math.floor(Math.random() * 3) + 1;
  }

  if (hour >= 10 && hour <= 16) {
    return Math.floor(Math.random() * 5) + 5;
  }

  return Math.floor(Math.random() * 4) + 2;
}

export function getWeatherAdvice(temp: number, description: string, humidity: number): string[] {
  const advice: string[] = [];

  if (temp < 5) {
    advice.push('Habillez-vous chaudement');
  } else if (temp > 30) {
    advice.push('Restez hydraté');
    advice.push('Évitez les efforts physiques intenses');
  }

  if (description.toLowerCase().includes('pluie')) {
    advice.push("N'oubliez pas votre parapluie");
  }

  if (humidity > 80) {
    advice.push('Humidité élevée - sensation de moiteur');
  }

  if (description.toLowerCase().includes('orage')) {
    advice.push('Évitez les activités en extérieur');
  }

  if (advice.length === 0) {
    advice.push('Conditions météo favorables');
  }

  return advice;
}
