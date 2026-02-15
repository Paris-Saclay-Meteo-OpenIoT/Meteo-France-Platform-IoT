'use client';
import React, { useState, useRef } from 'react';
import { FaDatabase } from 'react-icons/fa';

export default function DBPage() {
  const [activeDashboard, setActiveDashboard] = useState('redis');
  const [clickDisabled, setClickDisabled] = useState(false);


  // Dashboards URLs
  const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3000';
  const dashboards = {
    redis: `${grafanaUrl}/d/xDLNRKUWz/redis-dashboard?orgId=1&kiosk=1&theme=light`
  };

  // Handle dashboard click with loading control, prevent fetch errors
  const handleDashboardClick = (dashboardName) => {
    if (clickDisabled) return;
    setClickDisabled(true);
    setActiveDashboard(dashboardName);
    // Disable button for 2.5 seconds
    setTimeout(() => {
      setClickDisabled(false);
    }, 2500);
  };


  return (
    <div>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#191919]">Base de données</h1>
          <p className="text-gray-500">Lorem ipsum lorem lorem</p>
        </div>
      </div>

      {/* Selection Btns */}
      <div className="flex space-x-4 mb-4">
        <button
          onClick={() => handleDashboardClick('redis')}
          disabled={clickDisabled}
          className={`p-4 border rounded text-center w-32 ${
            activeDashboard === 'redis'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          <div className="flex justify-center mb-2">
            <FaDatabase size={24} />
          </div>
          <div className="text-sm">Redis</div>
        </button>
      </div>

      {/* Iframe */}
      <div>
        {activeDashboard === 'redis' && (
          <iframe
            title="Redis Dashboard"
            src={dashboards.redis}
            width="100%"
            height="600"
            allowFullScreen
            className="rounded-lg"
          ></iframe>
        )}
      </div>
    </div>
  );
}
