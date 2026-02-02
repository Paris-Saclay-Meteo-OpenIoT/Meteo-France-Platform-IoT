"use client";

import { useEffect, useRef, useState } from "react";
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
} from "chart.js";

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend
);

export default function ForecastPage() {
  const [view, setView] = useState("charts");
  const tempChartRef = useRef(null);
  const rainChartRef = useRef(null);
  const tempChartInstance = useRef(null);
  const rainChartInstance = useRef(null);

  // Données fictives (en attendant les vraies)
  const forecastData = [
    { date: "2025-04-10 04:00:00", temp: 8.97, rainProb: 0.78 },
    { date: "2025-04-10 05:00:00", temp: 8.74, rainProb: 0.78 },
    { date: "2025-04-10 06:00:00", temp: 8.71, rainProb: 0.78 },
    { date: "2025-04-10 07:00:00", temp: 9.27, rainProb: 0.78 },
    { date: "2025-04-10 08:00:00", temp: 10.78, rainProb: 0.91 },
    { date: "2025-04-10 09:00:00", temp: 13.07, rainProb: 0.78 },
    { date: "2025-04-10 10:00:00", temp: 15.36, rainProb: 0.78 },
    { date: "2025-04-10 11:00:00", temp: 16.92, rainProb: 0.70 },
    { date: "2025-04-10 12:00:00", temp: 17.67, rainProb: 0.78 },
    { date: "2025-04-10 13:00:00", temp: 17.95, rainProb: 0.78 },
    { date: "2025-04-10 14:00:00", temp: 17.97, rainProb: 0.78 },
    { date: "2025-04-10 15:00:00", temp: 17.70, rainProb: 0.78 },
    { date: "2025-04-10 16:00:00", temp: 16.95, rainProb: 0.78 },
    { date: "2025-04-10 17:00:00", temp: 15.86, rainProb: 0.78 },
    { date: "2025-04-10 18:00:00", temp: 14.88, rainProb: 0.78 },
    { date: "2025-04-10 19:00:00", temp: 14.15, rainProb: 0.78 },
    { date: "2025-04-10 20:00:00", temp: 13.64, rainProb: 0.78 },
    { date: "2025-04-10 21:00:00", temp: 13.28, rainProb: 0.78 },
    { date: "2025-04-10 22:00:00", temp: 12.99, rainProb: 0.70 },
    { date: "2025-04-10 23:00:00", temp: 12.74, rainProb: 0.78 },
  ];

  useEffect(() => {
    if (view !== "charts") {
      // On détruit les graphes quand on quitte la vue
      tempChartInstance.current?.destroy();
      rainChartInstance.current?.destroy();
      tempChartInstance.current = null;
      rainChartInstance.current = null;
      return;
    }
  
    if (!tempChartRef.current || !rainChartRef.current) return;
  
    const labels = forecastData.map(d => d.date.slice(11, 16));
  
    tempChartInstance.current = new Chart(tempChartRef.current, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Température prédite (°C)",
          data: forecastData.map(d => d.temp),
          borderColor: "red",
          borderWidth: 2,
          tension: 0.3,
        }],
      },
      options: {
        plugins: {
          legend: { labels: { color: "black" } },
        },
        scales: {
          x: { ticks: { color: "black" } },
          y: { ticks: { color: "black" } },
        },
      },
    });
  
    rainChartInstance.current = new Chart(rainChartRef.current, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Probabilité de précipitation (%)",
          data: forecastData.map(d => d.rainProb * 100),
          borderColor: "blue",
          borderWidth: 2,
          tension: 0.3,
        }],
      },
      options: {
        plugins: {
          legend: { labels: { color: "black" } },
        },
        scales: {
          x: { ticks: { color: "black" } },
          y: {
            ticks: { color: "black" },
            min: 0,
            max: 100,
          },
        },
      },
    });
  
    return () => {
      tempChartInstance.current?.destroy();
      rainChartInstance.current?.destroy();
    };
  }, [view, forecastData]);  

  return (
    <div className="w-[80%] mx-auto p-6">
      <h1 className="text-3xl font-bold text-blue-700 mb-4">
        Prévisions météorologiques
      </h1>
      <div className="flex justify-center gap-4 mb-6">
      <button
        onClick={() => setView("charts")}
        className={`px-4 py-2 rounded font-semibold ${
          view === "charts"
            ? "bg-blue-500 text-white"
            : "bg-gray-200 text-gray-700"
        }`}
      >
        📈 Graphiques
      </button>

      <button
        onClick={() => setView("table")}
        className={`px-4 py-2 rounded font-semibold ${
          view === "table"
            ? "bg-blue-500 text-white"
            : "bg-gray-200 text-gray-700"
        }`}
      >
        📋 Tableau
      </button>
    </div>

      {/* Graphique */}
      {view === "charts" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-4 rounded shadow-md">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">
              Température prédite
            </h2>
            <canvas ref={tempChartRef} />
          </div>

          <div className="bg-white p-4 rounded shadow-md">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">
              Probabilité de précipitation
            </h2>
            <canvas ref={rainChartRef} />
          </div>
        </div>
      )}

      {/* Tableau */}
      {view === "table" && (
        <div className="overflow-x-auto bg-white rounded shadow-md">
          <table className="w-full text-sm text-black">
            <thead className="bg-gray-200 text-left">
              <tr>
                <th className="p-2" >Date</th>
                <th className="p-2">Température prédite (°C)</th>
                <th className="p-2">Probabilité de precipitation (%)</th>
              </tr>
            </thead>
            <tbody>
              {forecastData.map((row, i) => (
                <tr key={i} className="border-t ">
                  <td className="p-2">{row.date}</td>
                  <td className="p-2">{row.temp.toFixed(1)}</td>
                  <td className="p-2">{(row.rainProb * 100).toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}