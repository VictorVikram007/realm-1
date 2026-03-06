/**
 * Map Module — Leaflet AQI Map with color-coded station markers
 */

const AQIMap = (() => {
    let map = null;
    let markersLayer = null;
    let nearbyMarkersLayer = null;
    let onCitySelect = null;

    const AQI_COLORS = {
        'Good': '#00e400',
        'Satisfactory': '#ffff00',
        'Moderate': '#ff7e00',
        'Poor': '#ff0000',
        'Very Poor': '#8f3f97',
        'Severe': '#7e0023',
    };

    function getAqiColor(aqi) {
        if (!aqi || aqi <= 0) return '#555';
        if (aqi <= 50) return AQI_COLORS['Good'];
        if (aqi <= 100) return AQI_COLORS['Satisfactory'];
        if (aqi <= 200) return AQI_COLORS['Moderate'];
        if (aqi <= 300) return AQI_COLORS['Poor'];
        if (aqi <= 400) return AQI_COLORS['Very Poor'];
        return AQI_COLORS['Severe'];
    }

    function getAqiBucket(aqi) {
        if (!aqi || aqi <= 0) return 'Unknown';
        if (aqi <= 50) return 'Good';
        if (aqi <= 100) return 'Satisfactory';
        if (aqi <= 200) return 'Moderate';
        if (aqi <= 300) return 'Poor';
        if (aqi <= 400) return 'Very Poor';
        return 'Severe';
    }

    function init(containerId, citySelectCallback) {
        onCitySelect = citySelectCallback;

        // Initialize map centered on India
        map = L.map(containerId, {
            zoomControl: true,
            scrollWheelZoom: true,
        }).setView([22.5, 79.0], 5);

        // Colorful tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 18,
        }).addTo(map);

        markersLayer = L.layerGroup().addTo(map);
        nearbyMarkersLayer = L.layerGroup().addTo(map);

        return map;
    }

    function loadStations(stations) {
        if (!markersLayer) return;
        markersLayer.clearLayers();

        // Group by city to avoid overlapping markers
        const cityMap = {};
        stations.forEach(s => {
            if (!s.lat || !s.lng) return;
            if (!cityMap[s.city]) {
                cityMap[s.city] = { ...s, count: 1 };
            } else {
                cityMap[s.city].count++;
            }
        });

        Object.values(cityMap).forEach(station => {
            // Skip stations without valid AQI data
            if (!station.aqi || station.aqi <= 0) return;

            const color = getAqiColor(station.aqi);
            const bucket = getAqiBucket(station.aqi);
            const radius = station.aqi ? Math.max(8, Math.min(20, station.aqi / 20)) : 8;

            const marker = L.circleMarker([station.lat, station.lng], {
                radius: radius,
                fillColor: color,
                color: 'rgba(255,255,255,0.3)',
                weight: 2,
                opacity: 0.9,
                fillOpacity: 0.75,
            });

            const popupContent = `
                <div style="font-family: 'Inter', sans-serif; min-width: 180px;">
                    <div style="font-size: 14px; font-weight: 700; margin-bottom: 6px;">
                        ${station.city}
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="background: ${color}; color: #000; padding: 2px 10px; border-radius: 12px; font-weight: 700; font-size: 13px;">
                            AQI: ${station.aqi || 'N/A'}
                        </span>
                        <span style="font-size: 12px; color: #94a3b8;">${bucket}</span>
                    </div>
                    <div style="font-size: 11px; color: #94a3b8;">
                        ${station.count > 1 ? station.count + ' monitoring stations' : station.name || '1 station'}
                    </div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                        ${station.state || ''}
                    </div>
                    <div style="margin-top: 8px;">
                        <button onclick="window.__selectCity && window.__selectCity('${station.city}')"
                                style="background: #3b82f6; color: white; border: none; padding: 4px 14px;
                                       border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
                                       font-family: 'Inter', sans-serif;">
                            View Forecast →
                        </button>
                    </div>
                </div>
            `;

            marker.bindPopup(popupContent);
            marker.on('click', () => {
                if (onCitySelect) onCitySelect(station.city);
            });

            markersLayer.addLayer(marker);
        });
    }

    function highlightCity(cityName, stations) {
        if (!map || !stations) return;

        // Find the first station matching the city name
        const cityStation = stations.find(s => s.city && s.city.toLowerCase() === cityName.toLowerCase() && s.lat && s.lng);

        if (cityStation) {
            // Re-center map and zoom into the city
            map.flyTo([cityStation.lat, cityStation.lng], 10, {
                animate: true,
                duration: 1.5
            });
        }
    }

    function resize() {
        if (map) {
            setTimeout(() => map.invalidateSize(), 100);
        }
    }

    function loadNearbyStations(stations) {
        if (!nearbyMarkersLayer) return;
        nearbyMarkersLayer.clearLayers();

        stations.forEach(station => {
            if (!station.lat || !station.lng || !station.aqi) return;

            const color = getAqiColor(station.aqi);
            const bucket = getAqiBucket(station.aqi);

            // Add a vibrant marker for nearby
            const marker = L.circleMarker([station.lat, station.lng], {
                radius: 10,
                fillColor: color,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.9,
            });

            // Make it pulse via css class if possible, or just standard for now
            const popupContent = `
                <div style="font-family: 'Inter', sans-serif; min-width: 160px;">
                    <div style="font-size: 13px; font-weight: 700; margin-bottom: 4px; color: #3b82f6;">Nearby Station</div>
                    <div style="font-size: 14px; font-weight: 700; margin-bottom: 6px;">
                        ${station.name}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">
                        ${station.city}
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="background: ${color}; color: #000; padding: 2px 10px; border-radius: 12px; font-weight: 700; font-size: 13px;">
                            AQI: ${station.aqi}
                        </span>
                        <span style="font-size: 12px; color: #94a3b8;">${bucket}</span>
                    </div>
                </div>
            `;

            marker.bindPopup(popupContent);
            marker.on('click', () => {
                if (onCitySelect) onCitySelect(station.city);
            });

            nearbyMarkersLayer.addLayer(marker);
        });
    }

    return { init, loadStations, highlightCity, resize, getAqiColor, getAqiBucket, loadNearbyStations };
})();
