"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { WiThermometer, WiHumidity, WiStrongWind, WiBarometer, WiRain } from "react-icons/wi";
import { Chart, LineController, LineElement, PointElement, BarController, BarElement, LinearScale, Title, CategoryScale, Tooltip } from "chart.js";
import { useAuth } from "../../context/AuthContext";

export default function StationDashboard() {
  const { id } = useParams(); // id = NUM_POSTE
  const [stationData, setStationData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [historyData, setHistoryData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [dayOffset, setDayOffset] = useState(0); // -6 (J-7) à 0 (aujourd'hui), 1 = prévisions
  const [forecastViewMode, setForecastViewMode] = useState("graph"); // "graph" ou "table"
  const { user, logout } = useAuth();
  const isAdminOrSci = user?.role === "admin" || user?.role === "scientifique";
  const isForecast = dayOffset === 1;

  const cache = useRef({
    "7d": { data: null, timestamp: 0 },
    "forecast_24h": { data: null, timestamp: 0 },
  });

  useEffect(() => {
    async function fetchData() {
      try {
        const backendHost =
          typeof window !== "undefined" && window.location.hostname === "localhost"
            ? "http://localhost:5000"
            : "http://ter_backend:5000";
  
        const response = await fetch(`${backendHost}/api/station/${id}`); // id = NUM_POSTE
  
        if (!response.ok) {
          console.warn(`Erreur ${response.status}: Station ${id} non trouvée`);
          setStationData(null);
          return;
        }
  
        const data = await response.json();
        if (!data) {
          console.warn("Données vides reçues");
          setStationData(null);
          return;
        }
        
        console.log("Données reçues :", data);
        setStationData(data);
      } catch (error) {
        console.warn("Erreur réseau:", error.message);
        setStationData(null);
      } finally {
        setLoading(false);
      }
    }
  
    if (id) fetchData();
  }, [id]);
  

 useEffect(() => {
  async function fetchHistory(force = false) {
    const key = "7d";
    const now = Date.now();
    const cacheEntry = cache.current[key];

    // Si cache valide (<5 min) et pas de rafraîchissement forcé
    if (!force && cacheEntry?.data && now - cacheEntry.timestamp < 5 * 60 * 1000) {
      setHistoryData(cacheEntry.data);
      return;
    }

    try {
      const backendHost =
        typeof window !== "undefined" && window.location.hostname === "localhost"
          ? "http://localhost:5000"
          : "http://ter_backend:5000";

      const endpoint = `${backendHost}/api/station/history/7d/${id}`;

      const response = await fetch(endpoint);
      if (!response.ok) {
        console.warn(`Erreur ${response.status}: Aucune donnée historique disponible.`);
        setHistoryData(null);
        return;
      }

      const data = await response.json();
      if (!Array.isArray(data) || data.length === 0) {
        console.warn("Données historiques vides");
        setHistoryData(null);
        return;
      }
      
      cache.current[key] = { data, timestamp: now };
      setHistoryData(data);
    } catch (error) {
      console.warn("Erreur fetch historique:", error.message);
      setHistoryData(null);
    }
  }

  if (stationData) {
    fetchHistory(); // Chargement initial (avec cache)
    const interval = setInterval(() => fetchHistory(true), 5 * 60 * 1000); // Rafraîchissement forcé

    return () => clearInterval(interval); // Nettoyage du timer si `stationData` change
  }
}, [stationData, id]); // Recharger les données historiques (7j)

// Effect pour récupérer les prédictions
useEffect(() => {
  async function fetchForecast(force = false) {
    const key = "forecast_24h";
    const now = Date.now();
    const cacheEntry = cache.current[key];

    // Si cache valide (<5 min) et pas de rafraîchissement forcé
    if (!force && cacheEntry?.data && now - cacheEntry.timestamp < 5 * 60 * 1000) {
      setForecastData(cacheEntry.data);
      return;
    }

    try {
      const backendHost =
        typeof window !== "undefined" && window.location.hostname === "localhost"
          ? "http://localhost:5000"
          : "http://ter_backend:5000";

      const endpoint = `${backendHost}/api/station/forecast/24h/${id}`;

      const response = await fetch(endpoint);
      if (!response.ok) {
        console.warn(`Erreur ${response.status}: Aucune prédiction disponible.`);
        setForecastData(null);
        return;
      }

      const data = await response.json();
      if (!Array.isArray(data) || data.length === 0) {
        console.warn("Données de prédiction vides");
        setForecastData(null);
        return;
      }
      
      cache.current[key] = { data, timestamp: now };
      setForecastData(data);
    } catch (error) {
      console.warn("Erreur fetch prédictions:", error.message);
      setForecastData(null);
    }
  }

  if (stationData && isForecast) {
    fetchForecast(); // Chargement initial (avec cache)
    const interval = setInterval(() => fetchForecast(true), 5 * 60 * 1000); // Rafraîchissement forcé

    return () => clearInterval(interval); // Nettoyage du timer si `stationData` change
  }
}, [stationData, isForecast, id]); // Recharger les prévisions
  function downloadDataAsJson(data, filename = "data.json") {
    try {
      if (!data || data.length === 0) {
        console.warn("Pas de données à télécharger");
        return;
      }
      
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
    
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
    
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Erreur téléchargement JSON:", error);
    }
  }

  function downloadChartAsPng(chartId, filename) {
    try {
      const chart = Chart.getChart(chartId);
      if (!chart) {
        console.warn("Chart non trouvé :", chartId);
        return;
      }
    
      const url = chart.toBase64Image();
      if (!url) {
        console.warn("Impossible de générer l'image pour :", chartId);
        return;
      }
      
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
    } catch (error) {
      console.error("Erreur export PNG:", error);
    }
  }
  function downloadAllChartsAsPng() {
    const charts = [
      { id: "tempChart", filename: `temperature.png` },
      { id: "humidityChart", filename: `humidite.png` },
      { id: "windChart", filename: `vent.png` },
      { id: "precipChart", filename: `precipitations.png` },
    ];
  
    let successCount = 0;
    charts.forEach(({ id, filename }) => {
      try {
        const chart = Chart.getChart(id);
        if (chart) {
          const url = chart.toBase64Image();
          const link = document.createElement("a");
          link.href = url;
          link.download = filename;
          link.click();
          successCount++;
        }
      } catch (error) {
        console.warn(`Erreur export ${filename}:`, error);
      }
    });
    
    if (successCount === 0) {
      console.warn("Aucun graphique n'a pu être exporté");
    }
  }
  
  
  

  useEffect(() => {
    try {
      // Filtrer les données selon le jour sélectionné
      let displayData;
      if (isForecast) {
        displayData = forecastData;
      } else if (historyData) {
        const targetDate = new Date();
        targetDate.setDate(targetDate.getDate() + dayOffset);
        const targetDateStr = targetDate.toDateString();
        displayData = historyData.filter(d => new Date(d.reference_time).toDateString() === targetDateStr);
      } else {
        displayData = null;
      }
      
      if (displayData && Array.isArray(displayData) && displayData.length > 0) {
        // Fonction pour normaliser les données (historique ou prédictions)
        const normalizeData = (dataPoint, isForecast) => {
          try {
            if (isForecast) {
              return {
                reference_time: dataPoint?.forecast_time,
                t: dataPoint?.t_pred,
                u: null,
                ff: dataPoint?.ff_pred,
                rr1: dataPoint?.rr1_pred,
              };
            } else {
              return {
                reference_time: dataPoint?.reference_time,
                t: dataPoint?.t,
                u: dataPoint?.u,
                ff: dataPoint?.ff,
                rr1: dataPoint?.rr1,
              };
            }
          } catch (error) {
            console.warn("Erreur normalisation données:", error);
            return { reference_time: null, t: null, u: null, ff: null };
          }
        };

        const normalizedData = displayData
          .map(d => normalizeData(d, isForecast))
          .filter(d => d && d.reference_time); // Filtrer les données invalides
      
        // Enregistrement de Chart.js et création des graphiques uniquement si les paramètres concernés sont disponibles
        Chart.register(LineController, LineElement, PointElement, BarController, BarElement, LinearScale, Title, CategoryScale, Tooltip);
    
        // Fonction pour détruire les anciens graphiques 
        const destroyChart = (chartId) => {
          const chart = Chart.getChart(chartId);
          if (chart) {
            chart.destroy();
          }
        };
    
        const ctxTemp = document.getElementById("tempChart")?.getContext("2d");
        const ctxHumidity = document.getElementById("humidityChart")?.getContext("2d");
        const ctxWind = document.getElementById("windChart")?.getContext("2d");  // Contexte pour le graphique du vent
        const ctxPrecip = document.getElementById("precipChart")?.getContext("2d"); // Contexte pour le graphique des précipitations
    
        // On détruit les anciens graphes pour afficher ceux de la période demandée
        destroyChart("tempChart");
        destroyChart("humidityChart");
        destroyChart("windChart");
        destroyChart("precipChart");
    
// Température
  if (ctxTemp && normalizedData.some((data) => data.t)) {
  const labels = normalizedData.map((data) => new Date(data.reference_time).toLocaleTimeString());
  const temperatureData = normalizedData.map((data) => data.t?.toFixed(1));

  new Chart(ctxTemp, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Température (°C)",
          data: temperatureData,
          borderColor: "red",
          borderWidth: 2,
          fill: false,
        },
      ],
    },
    options: {
      interaction: {
        mode: 'nearest',
        intersect: false,
      },
      plugins: {
        tooltip: {
          enabled: true,
          callbacks: {
            label: function (context) {
              const value = context.parsed.y;
              return  `🌡️${value} °C`;
            }
          }, 
          displayColors: false,
        },
        legend: {
          display: true,
        }
      },
      scales: {
        y: {
          title: {
            display: true,
            text: "Température (°C)",
            font: {
              size: 16,
              weight: "bold",
            },
          },
          ticks: {
            callback: (value) => value,
            stepSize: 0.5,
            min: 0.5, 
          },
        },
        x: {
          title: {
            display: true,
            text: "Heure",
            font: {
              size: 16,
              weight: "bold",
            },
          },
        },
      },
    }
    
  });
}

// Humidité
  if (ctxHumidity && !isForecast && normalizedData.some((data) => data.u)) {
  const labels = normalizedData.map((data) => new Date(data.reference_time).toLocaleTimeString());
  const humidityData = normalizedData.map((data) => data.u);

  new Chart(ctxHumidity, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Humidité (%)",
          data: humidityData,
          borderColor: "blue",
          borderWidth: 2,
          fill: false,
        },
      ],
    },
    options: {
      interaction: {
        mode: 'nearest',
        intersect: false,
      },
      plugins: {
        tooltip: {
          enabled: true,
          callbacks: {
            label: function (context) {
              const value = context.parsed.y;
              return `💧${value} %`;
            }
          },
          displayColors: false,
        },
        legend: {
          display: true,
        }
      },
      scales: {
        y: {
          title: {
            display: true,
            text: "Humidité (%)",
            font: {
              size: 16,
              weight: "bold",
            }
          },
          ticks: {
            callback: (value) => value,
            stepSize: 0.5,
            min: 0.5, 
          },
        },
        x: {
          title: {
            display: true,
            text: "Heure",
            font: {
              size: 16,
              weight: "bold",
            }
          },
        },
      },
    }
    
  });
}

// Vent
  if (ctxWind && normalizedData.some((data) => data.ff)) {
  const labels = normalizedData.map((data) => new Date(data.reference_time).toLocaleTimeString());
  const windSpeedData = normalizedData.map((data) => data.ff);

  new Chart(ctxWind, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Vitesse du vent (m/s)",
          data: windSpeedData,
          borderColor: "green",
          borderWidth: 2,
          fill: false,
        },
      ],
    },
    options: {
      interaction: {
        mode: 'nearest',
        intersect: false,
      },
      plugins: {
        tooltip: {
          enabled: true,
          callbacks: {
            label: function (context) {
              const value = context.parsed.y;
              return `🍃 ${value} m/s`;
            }
          },
          displayColors: false,
        },
        legend: {
          display: true,
        }
      },
      scales: {
        y: {
          title: {
            display: true,
            text: "Vitesse (m/s)",
            font: {
              size: 16,
              weight: "bold",
            }
          },
          ticks: {
            callback: (value) => value,
            stepSize: 0.5,
            min: 0.5, 
          },
        },
        x: {
          title: {
            display: true,
            text: "Heure",
            font: {
              size: 16,
              weight: "bold",
            }
          },
        },
      },
    },
  });
}

// Précipitations (masqué si tout est à 0)
  if (ctxPrecip && normalizedData.some((data) => data.rr1 != null && data.rr1 > 0)) {
  const labels = normalizedData.map((data) => new Date(data.reference_time).toLocaleTimeString());
  const precipData = normalizedData.map((data) => data.rr1 ?? 0);

  new Chart(ctxPrecip, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Précipitations (mm)",
          data: precipData,
          backgroundColor: "rgba(54, 162, 235, 0.5)",
          borderColor: "rgba(54, 162, 235, 1)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      interaction: {
        mode: 'nearest',
        intersect: false,
      },
      plugins: {
        tooltip: {
          enabled: true,
          callbacks: {
            label: function (context) {
              const value = context.parsed.y;
              return `🌧️ ${value} mm`;
            }
          },
          displayColors: false,
        },
        legend: {
          display: true,
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Précipitations (mm)",
            font: {
              size: 16,
              weight: "bold",
            }
          },
        },
        x: {
          title: {
            display: true,
            text: "Heure",
            font: {
              size: 16,
              weight: "bold",
            }
          },
        },
      },
    },
  });
}
      }
    } catch (error) {
      console.error("Erreur création graphiques:", error);
    }
  }, [historyData, forecastData, dayOffset, forecastViewMode]); // Données selon la periode demandée
  if (loading) {
    return <p className="text-center mt-10">⏳ Chargement des données...</p>;
  }
  
  if (!stationData) {
    return (
      <p className="text-center text-red-500 font-medium mt-10">
        ❌ Aucune donnée disponible pour cette station.
      </p>
    );
  }
  
  // Déclarer d'abord les constantes de base
  const temperatureC =
    stationData?.t !== undefined && stationData?.t !== null
      ? (stationData.t - 273.15).toFixed(1)
      : "N/A";
  const humidity = stationData?.u ?? "N/A";
  const windSpeed = stationData?.ff ?? "N/A";
  const windDirection = stationData?.dd ?? "N/A";
  const pressure = stationData?.pmer ? (stationData.pmer / 100).toFixed(2) : "N/A";
  const precipitation = stationData?.rr_per ?? "N/A";
  
  // Calculer les stats des prévisions (min/max/moy)
  const forecastStats = isForecast && forecastData?.length > 0 ? {
    t_min: Math.min(...forecastData.filter(d => d.t_pred != null).map(d => d.t_pred)).toFixed(1),
    t_max: Math.max(...forecastData.filter(d => d.t_pred != null).map(d => d.t_pred)).toFixed(1),
    t_avg: (forecastData.filter(d => d.t_pred != null).reduce((s, d) => s + d.t_pred, 0) / forecastData.filter(d => d.t_pred != null).length).toFixed(1),
    ff_avg: (forecastData.filter(d => d.ff_pred != null).reduce((s, d) => s + d.ff_pred, 0) / forecastData.filter(d => d.ff_pred != null).length).toFixed(1),
    rr1_total: forecastData.filter(d => d.rr1_pred != null).reduce((s, d) => s + d.rr1_pred, 0).toFixed(1),
  } : null;

  // Puis calculer displayTemperature en utilisant temperatureC
  const displayTemperature = isForecast && forecastStats
    ? `${forecastStats.t_min} — ${forecastStats.t_max}`
    : temperatureC;
  
  // Puis calculer lastDataTime
  const lastDataTime = historyData?.length > 0
    ? new Date(historyData[historyData.length - 1]?.reference_time).toLocaleString()
    : "Non disponible";

  // Date cible des prévisions
  const forecastTargetDate = forecastData?.length > 0
    ? new Date(forecastData[0]?.forecast_time).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
    : null;

  // Navigation : date sélectionnée et données filtrées
  const selectedDate = new Date();
  selectedDate.setDate(selectedDate.getDate() + dayOffset);
  const selectedDateLabel = selectedDate.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

  const filteredHistoryData = (() => {
    if (!historyData) return null;
    const targetDateStr = selectedDate.toDateString();
    const filtered = historyData.filter(d => new Date(d.reference_time).toDateString() === targetDateStr);
    return filtered.length > 0 ? filtered : null;
  })();

  const periodLabel = isForecast
    ? `prévisions ${forecastTargetDate || ''}`
    : dayOffset === 0
      ? "aujourd'hui"
      : selectedDateLabel;

    return (
      <div className="p-6 w-[90%] mx-auto text-center">
        <button
          onClick={() => window.history.back()}
          className="mb-4 px-4 py-2 bg-blue-500 text-white font-semibold rounded hover:bg-blue-600 self-start"
        >
          ← Retour
        </button>
    
        <h1 className="text-3xl font-bold text-blue-700 mb-6">
          Station météo : {stationData.name || id}
        </h1>
    
        {/* Navigation par jour avec flèches */}
        <div className="flex items-center justify-center gap-4 mb-4">
          <button
            onClick={() => setDayOffset(prev => Math.max(prev - 1, -6))}
            disabled={dayOffset <= -6}
            className={`text-2xl font-bold px-3 py-1 rounded transition-colors ${
              dayOffset <= -6 ? 'text-gray-300 cursor-not-allowed' : 'text-blue-600 hover:bg-blue-100 cursor-pointer'
            }`}
          >
            ◀
          </button>
          <div className="text-center min-w-[300px]">
            <p className="text-lg font-semibold">
              {isForecast
                ? (forecastData?.length > 0 ? `🔮 Prévisions — ${forecastTargetDate}` : '🔮 Prévisions indisponibles')
                : dayOffset === 0
                  ? `📅 Aujourd'hui — ${selectedDateLabel}`
                  : `📅 ${selectedDateLabel}`
              }
            </p>
            {!isForecast && dayOffset === 0 && (
              <p className="text-sm text-gray-500">Dernière mesure : {lastDataTime}</p>
            )}
          </div>
          <button
            onClick={() => setDayOffset(prev => Math.min(prev + 1, 1))}
            disabled={dayOffset >= 1}
            className={`text-2xl font-bold px-3 py-1 rounded transition-colors ${
              dayOffset >= 1 ? 'text-gray-300 cursor-not-allowed' : 'text-blue-600 hover:bg-blue-100 cursor-pointer'
            }`}
          >
            ▶
          </button>
        </div>
    
        <div className="grid grid-cols-1 gap-6 mt-4 text-gray-600">
          {/* Informations météo */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Température */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiThermometer size={40} className="text-red-500" />
              <h2 className="text-sm font-semibold mt-2">{isForecast ? 'Température (min — max)' : 'Température'}</h2>
              <p className="text-lg font-bold">{displayTemperature}°C</p>
              {isForecast && forecastStats && (
                <p className="text-xs text-gray-500">moy. {forecastStats.t_avg}°C</p>
              )}
            </div>
    
            {/* Humidité — masqué en mode prévision */}
            {!isForecast && (
              <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
                <WiHumidity size={40} className="text-blue-500" />
                <h2 className="text-sm font-semibold mt-2">Humidité</h2>
                <p className="text-lg font-bold">{humidity}%</p>
              </div>
            )}
    
            {/* Vent */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiStrongWind size={40} className="text-gray-700" />
              <h2 className="text-sm font-semibold mt-2">{isForecast ? 'Vent (moy.)' : 'Vent'}</h2>
              <p className="text-lg font-bold">{isForecast && forecastStats ? forecastStats.ff_avg : windSpeed} m/s</p>
              {!isForecast && <p className="text-sm">Direction : {windDirection}°</p>}
            </div>
    
            {/* Pression — masqué en mode prévision */}
            {!isForecast && (
              <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
                <WiBarometer size={40} className="text-green-600" />
                <h2 className="text-sm font-semibold mt-2">Pression</h2>
                <p className="text-lg font-bold">{pressure} hPa</p>
              </div>
            )}
    
            {/* Précipitations */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiRain size={40} className="text-blue-400" />
              <h2 className="text-sm font-semibold mt-2">{isForecast ? 'Précipitations (cumul)' : 'Précipitations'}</h2>
              <p className="text-lg font-bold">{isForecast && forecastStats ? forecastStats.rr1_total : precipitation} mm</p>
            </div>
          </div>
    
          {/* Graphiques et tableaux */}
          {isForecast && (!forecastData || forecastData.length === 0) ? (
  <div className="text-center mt-6 p-6 bg-orange-50 border border-orange-200 rounded-lg">
    <p className="text-orange-600 text-lg font-medium">🔮 Prévisions indisponibles pour cette station.</p>
  </div>
) : !isForecast && (!filteredHistoryData || filteredHistoryData.length === 0) ? (
  <div className="text-center mt-6 p-6 bg-blue-50 border border-blue-200 rounded-lg">
    <p className="text-blue-600 text-lg font-medium">📊 Aucune donnée disponible pour cette journée.</p>
  </div>
) : (
  (isForecast ? forecastData?.length > 0 : filteredHistoryData?.length > 0) && (
    <>
      {/* Toggle graphiques / tableaux (uniquement en mode prévisions, admin/sci) */}
      {isForecast && forecastData?.length > 0 && user && isAdminOrSci && (
        <div className="flex justify-center gap-2 mt-4 mb-2">
          <button
            onClick={() => setForecastViewMode("graph")}
            className={`py-2 px-4 font-semibold rounded transition-colors ${
              forecastViewMode === "graph"
                ? "bg-indigo-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            📈 Graphiques
          </button>
          <button
            onClick={() => setForecastViewMode("table")}
            className={`py-2 px-4 font-semibold rounded transition-colors ${
              forecastViewMode === "table"
                ? "bg-indigo-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            📋 Tableaux
          </button>
        </div>
      )}

      {/* Vue graphiques (historique ou prévisions en mode graph) */}
      {(!isForecast || forecastViewMode === "graph") && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
          {(isForecast ? forecastData?.some((data) => data.t_pred) : filteredHistoryData?.some((data) => data.t)) && (
            <div className="bg-white p-4 rounded-lg shadow-md">
              <h2 className="text-xl font-semibold text-center">{isForecast ? `Température (prévisions ${forecastTargetDate || ''})` : `Température (${periodLabel})`}</h2>
              <canvas id="tempChart" width="400" height="200"></canvas>
              {user && isAdminOrSci && (
                <button
                  onClick={() => downloadChartAsPng("tempChart", "temperature.png")}
                  className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  📷 Exporter
                </button>
              )}
            </div>
          )}

          {!isForecast && filteredHistoryData?.some((data) => data.u) && (
            <div className="bg-white p-4 rounded-lg shadow-md">
              <h2 className="text-xl font-semibold text-center">Humidité ({periodLabel})</h2>
              <canvas id="humidityChart" width="400" height="200"></canvas>
              {user && isAdminOrSci && (
                <button
                  onClick={() => downloadChartAsPng("humidityChart", "humidite.png")}
                  className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  📷 Exporter
                </button>
              )}
            </div>
          )}

          {(isForecast ? forecastData?.some((data) => data.ff_pred) : filteredHistoryData?.some((data) => data.ff)) && (
            <div className="bg-white p-4 rounded-lg shadow-md">
              <h2 className="text-xl font-semibold text-center">{isForecast ? `Vent (prévisions ${forecastTargetDate || ''})` : `Vent (${periodLabel})`}</h2>
              <canvas id="windChart" width="400" height="200"></canvas>
              {user && isAdminOrSci && (
                <button
                  onClick={() => downloadChartAsPng("windChart", "vent.png")}
                  className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  📷 Exporter
                </button>
              )}
            </div>
          )}

          {(isForecast ? forecastData?.some((data) => data.rr1_pred != null && data.rr1_pred > 0) : filteredHistoryData?.some((data) => data.rr1 != null && data.rr1 > 0)) && (
            <div className="bg-white p-4 rounded-lg shadow-md">
              <h2 className="text-xl font-semibold text-center">{isForecast ? `Précipitations (prévisions ${forecastTargetDate || ''})` : `Précipitations (${periodLabel})`}</h2>
              <canvas id="precipChart" width="400" height="200"></canvas>
              {user && isAdminOrSci && (
                <button
                  onClick={() => downloadChartAsPng("precipChart", "precipitations.png")}
                  className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  📷 Exporter
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Vue tableaux (prévisions uniquement) */}
      {isForecast && forecastViewMode === "table" && forecastData?.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          {/* Tableau Température */}
          <div className="bg-white p-3 rounded-lg shadow-md overflow-y-auto max-h-[420px]">
            <h3 className="text-sm font-semibold text-center mb-2 text-red-600">🌡️ Température (°C)</h3>
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0">
                <tr className="bg-red-50">
                  <th className="border border-gray-200 px-2 py-1 text-left">Heure</th>
                  <th className="border border-gray-200 px-2 py-1 text-right">°C</th>
                </tr>
              </thead>
              <tbody>
                {forecastData.filter(d => d.t_pred != null).map((d, i) => (
                  <tr key={`t-${d.forecast_time}`} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="border border-gray-200 px-2 py-1">{new Date(d.forecast_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="border border-gray-200 px-2 py-1 text-right font-mono">{d.t_pred.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Tableau Vent */}
          <div className="bg-white p-3 rounded-lg shadow-md overflow-y-auto max-h-[420px]">
            <h3 className="text-sm font-semibold text-center mb-2 text-green-600">💨 Vent (m/s)</h3>
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0">
                <tr className="bg-green-50">
                  <th className="border border-gray-200 px-2 py-1 text-left">Heure</th>
                  <th className="border border-gray-200 px-2 py-1 text-right">m/s</th>
                </tr>
              </thead>
              <tbody>
                {forecastData.filter(d => d.ff_pred != null).map((d, i) => (
                  <tr key={`ff-${d.forecast_time}`} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="border border-gray-200 px-2 py-1">{new Date(d.forecast_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="border border-gray-200 px-2 py-1 text-right font-mono">{d.ff_pred.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Tableau Précipitations */}
          <div className="bg-white p-3 rounded-lg shadow-md overflow-y-auto max-h-[420px]">
            <h3 className="text-sm font-semibold text-center mb-2 text-blue-600">🌧️ Précipitations (mm)</h3>
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0">
                <tr className="bg-blue-50">
                  <th className="border border-gray-200 px-2 py-1 text-left">Heure</th>
                  <th className="border border-gray-200 px-2 py-1 text-right">mm</th>
                </tr>
              </thead>
              <tbody>
                {forecastData.filter(d => d.rr1_pred != null).map((d, i) => (
                  <tr key={`rr-${d.forecast_time}`} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="border border-gray-200 px-2 py-1">{new Date(d.forecast_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="border border-gray-200 px-2 py-1 text-right font-mono">{d.rr1_pred.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
)}

</div>
    
{user && isAdminOrSci && (
<div className="mt-6 flex flex-wrap justify-center gap-4 w-full">
  {/* Bouton pour exporter les graphes */}
  {!(isForecast && forecastViewMode === "table") && (isForecast ? forecastData?.length > 0 : filteredHistoryData?.length > 0) && (
    <button
      onClick={() => downloadAllChartsAsPng()}
      className="py-2 px-4 bg-purple-500 text-white font-semibold rounded hover:bg-purple-600"
    >
      📦 Exporter les graphes
    </button>
  )}

  {/* Bouton pour télécharger les données */}
  {filteredHistoryData?.length > 0 && !isForecast && (
    <button
      onClick={() =>
        downloadDataAsJson(
          filteredHistoryData,
          `${stationData?.name || "station"}_${selectedDateLabel}.json`
        )
      }
      className="py-2 px-4 bg-blue-500 text-white font-semibold rounded hover:bg-blue-600"
    >
      💾 Télécharger les données
    </button>
  )}

  {/* Bouton pour télécharger les prévisions */}
  {forecastData?.length > 0 && isForecast && (
    <button
      onClick={() =>
        downloadDataAsJson(
          forecastData,
          `${stationData?.name || "station"}_previsions.json`
        )
      }
      className="py-2 px-4 bg-blue-500 text-white font-semibold rounded hover:bg-blue-600"
    >
      💾 Télécharger les prévisions
    </button>
  )}
</div>
)}
      </div>
    );  
}