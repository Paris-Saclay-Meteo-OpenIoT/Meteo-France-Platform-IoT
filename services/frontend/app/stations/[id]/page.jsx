"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { WiThermometer, WiHumidity, WiStrongWind, WiBarometer, WiRain } from "react-icons/wi";
import { Chart, LineController, LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip } from "chart.js";
import { useAuth } from "../../context/AuthContext";

export default function StationDashboard() {
  const { id } = useParams();
  const [stationData, setStationData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [historyData, setHistoryData] = useState(null);
  const [showSevenDays, setShowSevenDays] = useState(false); // Afficher les 7 derniers jours ou non
  const { user, logout } = useAuth();
  const isAdminOrSci = user?.role === "admin" || user?.role === "scientifique";

  const cache = useRef({
    "24h": { data: null, timestamp: 0 },
    "7d": { data: null, timestamp: 0 },
  });

  useEffect(() => {
    async function fetchData() {
      try {
        const backendHost =
          typeof window !== "undefined" && window.location.hostname === "localhost"
            ? "http://localhost:5000"
            : "http://ter_backend:5000";
  
        const response = await fetch(`${backendHost}/api/station/${id}`);
  
        if (!response.ok) {
          console.warn("Aucune donnée trouvée pour la station", id);
          setStationData(null);
          return;
        }
  
        const data = await response.json();
        console.log("Données reçues :", data);
        setStationData(data);
      } catch (error) {
        console.warn("Erreur réseau (peut être normale) :", error.message);
      } finally {
        setLoading(false);
      }
    }
  
    if (id) fetchData();
  }, [id]);
  

 useEffect(() => {
  async function fetchHistory(force = false) {
    const key = showSevenDays ? "7d" : "24h";
    const now = Date.now();
    const cacheEntry = cache.current[key];

    // Si cache valide (<5 min) et pas de rafraîchissement forcé
    if (!force && cacheEntry.data && now - cacheEntry.timestamp < 5 * 60 * 1000) {
      setHistoryData(cacheEntry.data);
      return;
    }

    try {
      const backendHost =
        typeof window !== "undefined" && window.location.hostname === "localhost"
          ? "http://localhost:5000"
          : "http://ter_backend:5000";

      const endpoint = showSevenDays
        ? `${backendHost}/api/station/history/7d/${id}`
        : `${backendHost}/api/station/history/24h/${id}`;

      const response = await fetch(endpoint);
      if (!response.ok) {
        console.warn("Aucune donnée historique disponible.");
        setHistoryData(null);
        return;
      }

      const data = await response.json();
      cache.current[key] = { data, timestamp: now };
      setHistoryData(data);
    } catch (error) {
      console.warn("Erreur fetch historique:", error);
      setHistoryData(null);
    }
  }

  if (stationData) {
    fetchHistory(); // Chargement initial (avec cache)
    const interval = setInterval(() => fetchHistory(true), 5 * 60 * 1000); // Rafraîchissement forcé

    return () => clearInterval(interval); // Nettoyage du timer si `stationData` change
  }
}, [stationData, showSevenDays]); // Recharger les données lorsque l'état showSevenDays change

  function downloadDataAsJson(data, filename = "data.json") {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
  
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
  
    URL.revokeObjectURL(url);
  }

  function downloadChartAsPng(chartId, filename) {
    const chart = Chart.getChart(chartId);
    if (!chart) {
      console.warn("Chart non trouvé :", chartId);
      return;
    }
  
    const url = chart.toBase64Image(); // Obtenir l'image
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
  }
  function downloadAllChartsAsPng(showSevenDays) {
    const suffix = showSevenDays ? "7jours" : "24h";
    const charts = [
      { id: "tempChart", filename: `temperature_${suffix}.png` },
      { id: "humidityChart", filename: `humidite_${suffix}.png` },
      { id: "windChart", filename: `vent_${suffix}.png` },
    ];
  
    charts.forEach(({ id, filename }) => {
      const chart = Chart.getChart(id);
      if (chart) {
        const url = chart.toBase64Image();
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
      }
    });
  }
  
  
  

  useEffect(() => {
    if (historyData) {
      // Enregistrement de Chart.js et création des graphiques uniquement si les paramètres concernés sont disponibles
      Chart.register(LineController, LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip);
  
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
  
      // On détruit les anciens graphes pour afficher ceux de la période demandée
      destroyChart("tempChart");
      destroyChart("humidityChart");
      destroyChart("windChart");
  
// Température
if (ctxTemp && historyData.some((data) => data.t)) {
  let labels, temperatureData;

  if (showSevenDays) {
    const groupedByDay = historyData.reduce((acc, data) => {
      const date = new Date(data.reference_time);
      const day = date.toLocaleDateString('fr-FR', { weekday: 'long' });
      if (!acc[day]) acc[day] = [];
      acc[day].push(data.t - 273.15); // conversion Kelvin -> Celsius
      return acc;
    }, {});

    labels = Object.keys(groupedByDay);
    temperatureData = labels.map(day => {
      const temps = groupedByDay[day];
      return (temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1);
    });
  } else {
    labels = historyData.map((data) => new Date(data.reference_time).toLocaleTimeString());
    temperatureData = historyData.map((data) => (data.t - 273.15).toFixed(1));
  }

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
            text: showSevenDays ? "Jour" : "Heure",
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
if (ctxHumidity && historyData.some((data) => data.u)) {
  let labels, humidityData;

  if (showSevenDays) {
    const groupedByDay = historyData.reduce((acc, data) => {
      const date = new Date(data.reference_time);
      const day = date.toLocaleDateString('fr-FR', { weekday: 'long' });
      if (!acc[day]) acc[day] = [];
      acc[day].push(data.u);
      return acc;
    }, {});

    labels = Object.keys(groupedByDay);
    humidityData = labels.map(day => {
      const humidityValues = groupedByDay[day];
      return (humidityValues.reduce((a, b) => a + b, 0) / humidityValues.length).toFixed(1);
    });
  } else {
    labels = historyData.map((data) => new Date(data.reference_time).toLocaleTimeString());
    humidityData = historyData.map((data) => data.u);
  }

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
            text: showSevenDays ? "Jour" : "Heure",
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
if (ctxWind && historyData.some((data) => data.ff)) {
  let labels, windSpeedData;

  if (showSevenDays) {
    const groupedByDay = historyData.reduce((acc, data) => {
      const date = new Date(data.reference_time);
      const day = date.toLocaleDateString('fr-FR', { weekday: 'long' });
      if (!acc[day]) acc[day] = [];
      acc[day].push(data.ff);
      return acc;
    }, {});

    labels = Object.keys(groupedByDay);
    windSpeedData = labels.map(day => {
      const windSpeeds = groupedByDay[day];
      return (windSpeeds.reduce((a, b) => a + b, 0) / windSpeeds.length).toFixed(1);
    });
  } else {
    labels = historyData.map((data) => new Date(data.reference_time).toLocaleTimeString());
    windSpeedData = historyData.map((data) => data.ff);
  }

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
            text: showSevenDays ? "Jour" : "Heure",
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
  }, [historyData, showSevenDays]); // Données selon la periode demandée
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
  
  const temperatureC =
    stationData.t !== undefined && stationData.t !== null
      ? (stationData.t - 273.15).toFixed(1)
      : "N/A";
  const humidity = stationData.u ?? "N/A";
  const windSpeed = stationData.ff ?? "N/A";
  const windDirection = stationData.dd ?? "N/A";
  const pressure = stationData.pmer ? (stationData.pmer / 100).toFixed(2) : "N/A";
  const precipitation = stationData.rr_per ?? "N/A";
  const lastDataTime = historyData?.length
    ? new Date(historyData[historyData.length - 1].reference_time).toLocaleString()
    : "Non disponible";

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
    
        <p className="text-lg font-semibold mb-4">📅 Dernière mesure : {lastDataTime}</p>
    
        <div className="grid grid-cols-1 gap-6 mt-4 text-gray-600">
          {/* Informations météo */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Température */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiThermometer size={40} className="text-red-500" />
              <h2 className="text-sm font-semibold mt-2">Température</h2>
              <p className="text-lg font-bold">{temperatureC}°C</p>
            </div>
    
            {/* Humidité */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiHumidity size={40} className="text-blue-500" />
              <h2 className="text-sm font-semibold mt-2">Humidité</h2>
              <p className="text-lg font-bold">{humidity}%</p>
            </div>
    
            {/* Vent */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiStrongWind size={40} className="text-gray-700" />
              <h2 className="text-sm font-semibold mt-2">Vent</h2>
              <p className="text-lg font-bold">{windSpeed} m/s</p>
              <p className="text-sm">Direction : {windDirection}°</p>
            </div>
    
            {/* Pression */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiBarometer size={40} className="text-green-600" />
              <h2 className="text-sm font-semibold mt-2">Pression</h2>
              <p className="text-lg font-bold">{pressure} hPa</p>
            </div>
    
            {/* Précipitations */}
            <div className="p-4 bg-white border rounded-lg shadow-md flex flex-col items-center">
              <WiRain size={40} className="text-blue-400" />
              <h2 className="text-sm font-semibold mt-2">Précipitations</h2>
              <p className="text-lg font-bold">{precipitation} mm</p>
            </div>
          </div>
    
          {/* Graphiques */}
          {historyData === null || historyData.length === 0 ? (
  <p className="text-center text-gray-500 text-lg font-medium mt-6">
    🕒 En attente de données historiques...
  </p>
) : (
  user && isAdminOrSci && (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
      {historyData.some((data) => data.t) && (
        <div className="bg-white p-4 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-center">Température ({showSevenDays ? '7 jours' : '24h'})</h2>
          <canvas id="tempChart" width="400" height="200"></canvas>
          <button
        onClick={() => downloadChartAsPng("tempChart", "temperature.png")}
        className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        📷 Exporter
      </button>
        </div>
      )}

      {historyData.some((data) => data.u) && (
        <div className="bg-white p-4 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-center">Humidité ({showSevenDays ? '7 jours' : '24h'})</h2>
          <canvas id="humidityChart" width="400" height="200"></canvas>
          <button
        onClick={() => downloadChartAsPng("humidityChart", "humidite.png")}
        className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        📷 Exporter
      </button>
        </div>
      )}

      {historyData.some((data) => data.ff) && (
        <div className="bg-white p-4 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-center">Vent ({showSevenDays ? '7 jours' : '24h'})</h2>
          <canvas id="windChart" width="400" height="200"></canvas>
          <button
        onClick={() => downloadChartAsPng("windChart", "vent.png")}
        className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        📷 Exporter
      </button>
        </div>
      )}
    </div>
  )
)}

</div>
    
<div className="mt-6 flex flex-wrap justify-center gap-4 w-full">
  {/* Bouton pour changer de période */}
  <button
    onClick={() => setShowSevenDays(!showSevenDays)}
    className="py-2 px-4 bg-green-500 text-white font-semibold rounded hover:bg-green-600"
  >
    Afficher les {showSevenDays ? "24 dernières heures" : "7 derniers jours"}
  </button>

  {user && isAdminOrSci && (
    <>
      {/* Bouton pour exporter les graphes */}
      <button
        onClick={() => downloadAllChartsAsPng(showSevenDays)}
        className="py-2 px-4 bg-purple-500 text-white font-semibold rounded hover:bg-purple-600"
      >
        📦 Exporter les graphes sur {showSevenDays ? "7 jours" : "24h"}
      </button>

      {/* Bouton pour télécharger les données */}
      {historyData && (
        <button
          onClick={() =>
            downloadDataAsJson(
              historyData,
              `${stationData.name}_${showSevenDays ? "7jours" : "24h"}.json`
            )
          }
          className="py-2 px-4 bg-blue-500 text-white font-semibold rounded hover:bg-blue-600"
        >
          💾 Télécharger les données {showSevenDays ? "sur 7 jours" : "sur 24h"}
        </button>
      )}
    </>
  )}

</div>
      </div>
    );  
}