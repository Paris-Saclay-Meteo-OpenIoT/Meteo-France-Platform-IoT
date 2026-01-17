'use client';
import React, { useState } from 'react';
import { FaChartBar, FaDocker } from 'react-icons/fa';
import { SiApachekafka } from 'react-icons/si';

export default function SystemPage() {
  const [activeDashboard, setActiveDashboard] = useState('node');
  const [clickDisabled, setClickDisabled] = useState(false);

  // Dashboard URLs
  const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL || "http://localhost:3000";
  const dashboards = {
    node: `${grafanaUrl}/d/rYdddlPWk/node-exporter-dashboard?orgId=1&kiosk=1&theme=light`,
    docker: `${grafanaUrl}/d/pMEd7m0Mz/cadvisor-dashboard?orgId=1&kiosk=1&theme=light`,
    kafka: `${grafanaUrl}/d/jwPKIsniz/kafka-dashboard?orgId=1&kiosk=1&theme=light`,
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
          <h1 className="text-2xl font-bold text-[#191919]">Système</h1>
          <p className="text-gray-500">Lorem ipsum lorem lorem</p>
        </div>
      </div>

      {/* Select Btns */}
      <div className="flex space-x-4 mb-4">
        <button
          onClick={() => handleDashboardClick('node')}
          disabled={clickDisabled}
          className={`
            p-4 border shadow rounded-lg text-center w-32 
            hover:scale-105 hover:shadow-lg transition-transform duration-300
            ${activeDashboard === 'node' ? 'bg-blue-500 text-white' : 'bg-white border-gray-200 text-gray-700'}
          `}
        >
          <div className="flex justify-center mb-2">
            <FaChartBar size={24} />
          </div>
          <div className="text-sm">Metric System</div>
        </button>

        <button
          onClick={() => handleDashboardClick('docker')}
          disabled={clickDisabled}
          className={`
            p-4 border shadow rounded-lg text-center w-32 
            hover:scale-105 hover:shadow-lg transition-transform duration-300            
            ${activeDashboard === 'docker' ? 'bg-blue-500 text-white' : 'bg-white border-gray-200 text-gray-700'}
          `}
        >
          <div className="flex justify-center mb-2">
            <FaDocker size={24} />
          </div>
          <div className="text-sm">Metric Container</div>
        </button>

        <button
          onClick={() => handleDashboardClick('kafka')}
          disabled={clickDisabled}
          className={`
            p-4 border shadow rounded-lg text-center w-32 
            hover:scale-105 hover:shadow-lg transition-transform duration-300            
            ${activeDashboard === 'kafka' ? 'bg-blue-500 text-white' : 'bg-white border-gray-200 text-gray-700'}
          `}
        >
          <div className="flex justify-center mb-2">
            <SiApachekafka size={24} />
          </div>
          <div className="text-sm">Metric Broker</div>
        </button>
      </div>

      {/* Iframe */}
      <div>
        {activeDashboard === 'node' && (
          <iframe
            title="Metric System Dashboard"
            src={dashboards.node}
            width="100%"
            height="600"
            allowFullScreen
            className="rounded-lg"
          ></iframe>
        )}
        {activeDashboard === 'docker' && (
          <iframe
            title="Metric Container Dashboard"
            src={dashboards.docker}
            width="100%"
            height="600"
            allowFullScreen
            className="rounded-lg"
          ></iframe>
        )}
        {activeDashboard === 'kafka' && (
          <iframe
            title="Metric Broker Dashboard"
            src={dashboards.kafka}
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
