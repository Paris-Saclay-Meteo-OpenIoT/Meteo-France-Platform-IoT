"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import corseStations from "../data/corseStations"; // Import des stations corses

// Fonction pour formater le nom des stations
const formatStationName = (name) => {
  let formattedName = name.replace(/[_-](.)/g, (match, p1) => " " + p1.toUpperCase());
  formattedName = formattedName
    .toLowerCase()
    .replace(/(?:^|\s)\S/g, (match) => match.toUpperCase());
  return formattedName;
};

export default function MapPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [regionFilter] = useState("All");
  const [filteredStations, setFilteredStations] = useState(corseStations); // Initialisation avec les stations corses
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined" && window.L) {
      if (window.L.DomUtil.get("map")?._leaflet_id != null) {
        window.L.DomUtil.get("map")._leaflet_id = null;
      }

      const map = window.L.map("map").setView([42.1, 9], 8.5); // Positionner la carte sur la Corse
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      }).addTo(map);

      filteredStations.forEach((station) => {
        const lat = station.geometry.coordinates[1];
        const lon = station.geometry.coordinates[0];
        const marker = window.L.marker([lat, lon], { clickable: false }).addTo(map);
        const popupContent = `
          <div style="text-align: center;">
            <b>${station.properties.NOM_USUEL}</b><br>
            <button 
              onclick="window.location.href='/stations/${station.properties.NUM_POSTE}'"
              style="
                margin-top: 5px;
                padding: 5px 10px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;"
            >
              Info
            </button>
          </div>
        `;
        marker.bindPopup(popupContent);
      });

      return () => map.remove();
    }
  }, [filteredStations]);

  const handleSearch = (event) => {
    const search = event.target.value.toLowerCase();
    setSearchTerm(search);
    filterStations(search, regionFilter);
  };

  const filterStations = (search) => {
      let results = corseStations;
      results = results.filter((station) =>
      station.properties.NOM_USUEL.toLowerCase().includes(search)
    );
    setFilteredStations(results);
  };

  return (
    <div className="flex flex-col lg:flex-row w-[80%] mx-auto">
      <div className="w-full lg:w-2/3 p-6">
        <h1 className="text-3xl sm:text-2xl font-bold text-blue-700 mb-4">Carte des stations météo corses</h1>
        <div id="map" className="w-full h-[calc(100vh-200px)] border rounded shadow-md"></div>
      </div>

      <div className="w-full lg:w-1/3 p-6 flex flex-col"> 
        <h2 className="text-2xl font-bold text-orange-600 mb-4">Liste des stations</h2>
        <input
          type="text"
          placeholder="Rechercher..."
          value={searchTerm}
          onChange={handleSearch}
          className="w-full sm:w-[90%] p-2 text-black border rounded mb-4"
        />
        <div className="flex-1 overflow-y-auto"> {}
          <ul className="max-h-[calc(100vh-300px)] overflow-y-auto">
            {filteredStations.map((station, index) => (
              <li
                key={index}
                className="p-2 sm:p-1 border rounded mb-2 cursor-pointer hover:bg-blue-500 hover:text-white"
                onClick={() => router.push(`/stations/${station.properties.NUM_POSTE}`)}
              >
                {formatStationName(station.properties.NOM_USUEL)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}