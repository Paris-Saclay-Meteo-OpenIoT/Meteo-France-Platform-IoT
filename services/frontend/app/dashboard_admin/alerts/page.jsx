"use client";
import React, { useState, useEffect } from "react";
import { io } from "socket.io-client";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "react-toastify";
import AlertTypeCard from "./components/AlertTypeCard";
import AlertCard from "./components/AlertCard";

// Icons
import { BsDatabaseExclamation } from "react-icons/bs";
import { LuMonitorX } from "react-icons/lu";
import { MdOutlineSignalWifiStatusbarConnectedNoInternet4 } from "react-icons/md";
import { FaDocker } from "react-icons/fa";

// Icons mapping for alert categories
const alertTypeIcon = {
  api: MdOutlineSignalWifiStatusbarConnectedNoInternet4,
  system: LuMonitorX,
  database: BsDatabaseExclamation,
  docker: FaDocker,
};

// Initial alert types for statistics and filtering
const initialAlertTypes = [
  { key: "api", label: "Alertes API's", icon: alertTypeIcon.api, backgroundColor: "bg-[#969ba9]" },
  { key: "system", label: "Alertes système", icon: alertTypeIcon.system, backgroundColor: "bg-[#df695a]" },
  { key: "database", label: "Alertes DB", icon: alertTypeIcon.database, backgroundColor: "bg-[#8ebda8]" },
  { key: "docker", label: "Alertes Docker", icon: alertTypeIcon.docker, backgroundColor: "bg-[#7da6cf]" },
];

export default function AlertPage() {
  const [alerts, setAlerts] = useState([]); // Store alerts in state
  // Count of alerts by category
  const [alertCount, setAlertCount] = useState({
    api: 0,
    system: 0,
    database: 0,
    docker: 0,
  });
  const [displayMode, setDisplayMode] = useState("active"); // State for display mode (active or archived)
  const [searchTerm, setSearchTerm] = useState(""); // State for search term
  const [filterCategory, setFilterCategory] = useState("all"); // State for category filter

  // Mapping function to convert alert data to a common format
  const mapAlert = (alert) => {
    
    let uniqueKey = alert.key || alert.alert_key;

    if (!uniqueKey || uniqueKey.includes('unknown') || uniqueKey.startsWith('DatasourceNoData')) {
       const baseName = alert.labels?.alertname || alert.alert_name || 'alert';
       const timestamp = alert.startsAt || alert.received_at || Date.now();
       uniqueKey = `generated-${baseName}-${timestamp}-${Math.random().toString(36).substr(2, 5)}`;
    }

    const title = alert.annotations?.summary 
                  || alert.alert_name 
                  || alert.labels?.alertname 
                  || "Sans titre";

    const name = alert.labels?.container 
                 || alert.labels?.name 
                 || alert.container 
                 || "Système";

    const description = alert.annotations?.description 
                        || alert.description 
                        || "Pas de description";

    const time = alert.startsAt || alert.received_at || new Date().toISOString();
    
    const category = alert.labels?.category 
                      || alert.category
                      || "system"; 

    return {
      title,
      name,
      description,
      time,
      category,
      status: alert.status || "active",
      icon: alertTypeIcon[category] || alertTypeIcon.system,
      key: uniqueKey, 
    };
  };

  // Add or update an alert in the state
  const upsertAlert = (newAlert) => {
    setAlerts((prev) => {
      const index = prev.findIndex((alert) => alert.key === newAlert.key);
      if (index !== -1) {
        // Replace the alert if it already exists
        const updated = [...prev];
        updated[index] = newAlert;
        return updated;
      } else {
        // Inc counter for the category
        setAlertCount((prevCount) => {
          const cat = newAlert.category || "system";
          return { ...prevCount, [cat]: (prevCount[cat] || 0) + 1 };
        });
        return [...prev, newAlert];
      }
    });
  };

  // Remove an alert from the state
  const removeAlert = (key, category) => {
    setAlerts((prev) => prev.filter((alert) => alert.key !== key));
    setAlertCount((prev) => ({
      ...prev,
      [category]: Math.max((prev[category] || 1) - 1, 0),
    }));
  };

  // Archive an alert and remove it from the state (and update the backend)
  const archiveAlert = async (alertKey, category) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
      const res = await fetch(`${backendUrl}/api/alerts/archive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: alertKey }),
      });
      if (res.ok) {
        removeAlert(alertKey, category);
        toast.success("Alerte archivée avec succès");
      } else {
        toast.error("Erreur lors de l'archivage de l'alerte");
      }
    } catch (err) {
      console.error("Erreur lors de la requête d'archivage :", err);
    }
  };

  // Fetch initial alerts on component mount
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const endpoint = displayMode === "active" ? "/api/alerts" : "/api/alerts/archived";
        const res = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000") + endpoint);
        if (res.ok) {
          const data = await res.json();
          const mapped = data.map(mapAlert);
          setAlerts(mapped);
          const counts = mapped.reduce((acc, alert) => {
            const cat = alert.category || "system";
            acc[cat] = (acc[cat] || 0) + 1;
            return acc;
          }, {});
          setAlertCount(counts);
          // Reset the category filter after change
          setFilterCategory("all");
        } else {
          console.error("Erreur lors du chargement initial des alertes :", res.statusText);
        }
      } catch (err) {
        console.error("Erreur lors de la requête initiale des alertes :", err);
      }
    };

    fetchAlerts();
  }, [displayMode]);

  // Socket.IO connection for real-time alerts 
  useEffect(() => {
    if (displayMode !== "active") return;
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
    const socket = io(backendUrl);
    socket.on("connect", () => {
      console.log("Connecté avec Socket.IO, id:", socket.id);
    });
    socket.on("alert", (data) => {
      if (data && data.labels) {
        const newAlert = mapAlert(data);
        upsertAlert(newAlert);
      } else {
        setAlerts((prev) => [...prev, data]);
      }
    });
    socket.on("alertUpdate", (data) => {
      console.log("Mise à jour d'une alerte :", data);
      if (data && data.labels) {
        const updatedAlert = mapAlert(data);
        upsertAlert(updatedAlert);
      }
    });
    // Cleaning
    return () => {
      socket.disconnect();
    };
  }, [displayMode]);

// Filter alerts based on search term and category 
  const filteredAlerts = alerts.filter((alert) => {

    const term = searchTerm.toLowerCase();
    const matchesSearch =
      alert.title.toLowerCase().includes(term) ||
      alert.name.toLowerCase().includes(term) ||
      alert.description.toLowerCase().includes(term);

    const matchesCategory = filterCategory === "all" || alert.category === filterCategory;

    // On garde l'alerte seulement si elle match la recherche ET la catégorie
    return matchesSearch && matchesCategory;
  });

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#191919]">Alertes</h1>
          <p className="text-gray-500">Lorem ipsum lorem lorem</p>
        </div>
      </div>

      {/* Btn toggle between active and archives */}
      <div className="flex space-x-4 mb-4">
        <button
          onClick={() => setDisplayMode("active")}
          className={`px-4 py-2 rounded-md shadow-sm border ${
            displayMode === "active" ? "bg-blue-600 text-white" : "bg-white text-gray-700"
          }`}
        >
          Alertes actives
        </button>
        <button
          onClick={() => setDisplayMode("archived")}
          className={`px-4 py-2 rounded-md shadow-sm border ${
            displayMode === "archived" ? "bg-blue-600 text-white" : "bg-white text-gray-700"
          }`}
        >
          Alertes archivées
        </button>
      </div>

      {/* Category cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {initialAlertTypes.map((type) => (
          <AlertTypeCard
            key={type.key}
            count={type.key === "all" ? alerts.length : alertCount[type.key] || 0}
            label={type.label}
            icon={type.icon}
            backgroundColor={type.backgroundColor}
            // If the filter is already set to the current category, reset it to "all"
            onClick={() => setFilterCategory((prev) => (prev === type.key ? "all" : type.key))}
            selected={filterCategory === type.key || (type.key === "all" && filterCategory === "all")}
          />
        ))}
      </div>

      {/* Searchbar */}
      <div className="flex flex-wrap items-center gap-2 mb-6 justify-between">
        <div className="relative w-full max-w-sm">
          <input
            type="text"
            placeholder="Rechercher des alertes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full text-black pl-8 pr-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <svg
            className="absolute left-2 top-2.5 w-5 h-5 text-[#9D9D9D]"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>
        <input
          type="date"
          className="border border-gray-200 rounded-md px-2 py-1.5 outline-none focus:ring-2 focus:ring-blue-500 text-gray-400"
        />
      </div>

      {/* Dynamic alert grid */}
      <AnimatePresence>
        {filteredAlerts.length === 0 ? (
          <div className="flex justify-center items-center h-full col-span-full">
            <p className="text-gray-500 text-xl">Aucune alerte en cours</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAlerts.map((alert) => {
              const IconComponent = alert.icon;
              return (
                <motion.div
                  key={alert.key}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.5 }}
                >
                  <AlertCard
                    key={alert.key}
                    title={alert.title}
                    name={alert.name}
                    time={alert.time}
                    description={alert.description}
                    category={alert.category}
                    status={alert.status}
                    icon={<IconComponent className="w-8 h-8" />}
                    onArchive={() => archiveAlert(alert.key, alert.category)}
                  />
                </motion.div>
              );
            })}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
