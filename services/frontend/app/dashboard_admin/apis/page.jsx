export default function APIPage() {
    const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL || `${typeof window !== 'undefined' ? window.location.protocol : 'http:'}//${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:3000`;
    return (
      <div>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[#191919]">API's</h1>
            <p className="text-gray-500">Lorem ipsum lorem lorem</p>
          </div>
        </div>
        {/* Iframe */}
        <iframe 
          src={`${grafanaUrl}/d/aee8hut2g4ykgf/api-dashboard?orgId=1&kiosk=1&theme=light`}
          width="100%" 
          height="600" 
          title="Dashboard Grafana"
        ></iframe>
      </div>
    );
  }
  