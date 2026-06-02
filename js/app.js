/**
 * App Module — Main application logic
 * Orchestrates map, charts, advisory, and API communication
 */

(() => {
    'use strict';

    const API_BASE = '';  // Same origin (served by Flask)

    let allCities = [];
    let allStations = [];
    let selectedCity = null;

    // ── Initialization ──────────────────────────────────────
    document.addEventListener('DOMContentLoaded', async () => {
        // Create background particles
        createParticles();

        // Initialize components
        AQIMap.init('aqi-map', onCitySelect);
        AQICharts.initForecastChart('forecast-chart');
        AQICharts.initHistoryChart('history-chart');
        Advisory.init(onGroupChange);

        // Global callback for map popup buttons
        window.__selectCity = onCitySelect;

        // Setup search
        setupSearch();

        // Model type selector — re-fetch forecast when changed
        const modelSelect = document.getElementById('model-type-select');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                if (selectedCity) onCitySelect(selectedCity);
            });
        }

        // Load initial data
        await loadInitialData();

        // Ensure loader is hidden
        const loader = document.getElementById('loading-overlay');
        if (loader) loader.classList.add('hidden');
    });

    // ── Data Loading ────────────────────────────────────────
    async function loadInitialData() {
        try {
            // Load cities and stations in parallel
            const [citiesRes, stationsRes, healthRes] = await Promise.all([
                fetch(`${API_BASE}/api/cities`).then(r => r.json()),
                fetch(`${API_BASE}/api/stations`).then(r => r.json()),
                fetch(`${API_BASE}/api/health`).then(r => r.json()),
            ]);

            if (citiesRes.status === 'ok') {
                allCities = citiesRes.cities;
                renderRankings(allCities);
            }

            if (stationsRes.status === 'ok') {
                allStations = stationsRes.stations;
                AQIMap.loadStations(allStations);
            }

            // Update API status
            updateApiStatus(healthRes);

            // Auto-select Delhi if available
            if (allCities.length > 0) {
                const delhi = allCities.find(c => c.city === 'Delhi');
                onCitySelect(delhi ? 'Delhi' : allCities[0].city);
            }

        } catch (error) {
            console.error('Failed to load initial data:', error);
            updateApiStatus({ status: 'error' });
        }
    }

    // ── City Selection ──────────────────────────────────────
    async function onCitySelect(cityName) {
        if (!cityName) return;
        selectedCity = cityName;

        // Update hero
        updateHero(cityName);

        // Highlight on map
        AQIMap.highlightCity(cityName, allStations);

        // Fetch nearby based on city coords
        const cityStation = allStations.find(s => s.city === cityName && s.lat && s.lng);
        let nearbyPromise = Promise.resolve({ status: 'none', stations: [] });
        if (cityStation) {
            nearbyPromise = fetch(`${API_BASE}/api/nearby?lat=${cityStation.lat}&lng=${cityStation.lng}`).then(r => r.json());
            document.getElementById('nearby-section')?.classList.remove('hidden');
            const grid = document.getElementById('nearby-grid');
            if (grid) grid.innerHTML = `<div class="nearby-loading"><div class="loader-ring" style="width: 30px; height: 30px; border-width: 2px;"></div><p>Locating nearby stations...</p></div>`;
            const badge = document.getElementById('nearby-count-badge');
            if (badge) badge.textContent = '...';
        } else {
            document.getElementById('nearby-section')?.classList.add('hidden');
        }

        // Load forecast, history, and advisory in parallel
        const group = Advisory.getGroup();

        try {
            const modelType = document.getElementById('model-type-select')?.value || 'xgboost';
            const modelLoading = document.getElementById('model-loading');
            if (modelLoading) modelLoading.classList.remove('hidden');

            const [forecastRes, historyRes, realtimeRes, nearbyRes] = await Promise.all([
                fetch(`${API_BASE}/api/predict/${encodeURIComponent(cityName)}?model_type=${modelType}`).then(r => r.json()),
                fetch(`${API_BASE}/api/historical/${encodeURIComponent(cityName)}`).then(r => r.json()),
                fetch(`${API_BASE}/api/realtime/${encodeURIComponent(cityName)}`).then(r => r.json()),
                nearbyPromise
            ]);

            if (modelLoading) modelLoading.classList.add('hidden');

            if (realtimeRes.status === 'ok') {
                // Update hero again with fresh real-time data
                updateHero(cityName, realtimeRes.data, realtimeRes.weather);
            }

            if (forecastRes.status === 'ok') {
                updateForecast(forecastRes, cityName);
                // Get advisory based on real-time AQI or predicted AQI
                const aqiForAdvisory = (realtimeRes.status === 'ok' && realtimeRes.data.aqi)
                    ? realtimeRes.data.aqi
                    : (forecastRes.current_aqi || 0);
                loadAdvisory(aqiForAdvisory, group);
            }

            if (historyRes.status === 'ok') {
                AQICharts.updateHistoryChart(historyRes.history);
                document.getElementById('history-city-label').textContent =
                    `${cityName} — Last ${historyRes.history.length} days`;
            }

            if (nearbyRes && nearbyRes.status === 'ok') {
                renderNearby(nearbyRes.stations || [], cityName);
                if (AQIMap.loadNearbyStations) AQIMap.loadNearbyStations(nearbyRes.stations || []);
            } else if (cityStation) {
                renderNearby([], cityName);
            }

        } catch (error) {
            console.error(`Error loading data for ${cityName}:`, error);
        }
    }

    function updateHero(cityName, realtimeData = null, weatherData = null) {
        document.getElementById('hero-city-name').textContent = cityName;

        let aqi = 0;
        let pData = {};
        let dtDisplay = '';

        if (realtimeData && realtimeData.time) {
            // AQICN format overrides
            aqi = parseFloat(realtimeData.aqi) || 0;
            pData = realtimeData.pollutants || {};

            try {
                // Parse AQICN time format reliably (API sends local time)
                const dt = new Date(realtimeData.time.replace(/-/g, '/'));
                dtDisplay = dt.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
                // If invalid date, fallback to raw string
                if (dtDisplay === 'Invalid Date') dtDisplay = realtimeData.time;
            } catch (e) {
                dtDisplay = realtimeData.time;
            }
        } else {
            // Dataset fallback
            const cityData = allCities.find(c => c.city === cityName);
            if (cityData) {
                aqi = cityData.aqi || 0;
                pData = cityData;
                if (cityData.datetime) {
                    const dt = new Date(cityData.datetime);
                    dtDisplay = dt.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
                }
            }
        }

        document.getElementById('hero-datetime').textContent = dtDisplay;
        animateNumber('aqi-number', aqi);
        updateAqiRing(aqi);
        updateAqiBucket(aqi);
        updatePollutants(pData);
        updateWeatherWidget(weatherData);
    }

    function updateWeatherWidget(weatherData) {
        const widget = document.getElementById('weather-widget');
        if (!widget) return;

        if (weatherData && weatherData.temp_c !== undefined) {
            widget.classList.remove('hidden');
            document.getElementById('weather-icon-img').src = weatherData.condition_icon.replace('64x64', '128x128');
            document.getElementById('weather-temp').textContent = `${Math.round(weatherData.temp_c)}°C`;
            document.getElementById('weather-condition').innerHTML = `${weatherData.condition_text} <br> 💨 ${weatherData.wind_kph} km/h`;
        } else {
            widget.classList.add('hidden');
        }
    }

    function animateNumber(elementId, target) {
        const el = document.getElementById(elementId);
        if (!el) return;

        const start = parseInt(el.textContent) || 0;
        const duration = 800;
        const startTime = performance.now();

        function frame(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            const current = Math.round(start + (target - start) * eased);
            el.textContent = current;

            // Update color
            el.style.color = getAqiColorHex(current);

            if (progress < 1) requestAnimationFrame(frame);
        }

        requestAnimationFrame(frame);
    }

    function updateAqiRing(aqi) {
        const ring = document.getElementById('aqi-ring-fill');
        if (!ring) return;

        const circumference = 2 * Math.PI * 54; // r=54
        const percent = Math.min(aqi / 500, 1);
        const offset = circumference * (1 - percent);

        ring.style.strokeDashoffset = offset;
        ring.style.stroke = getAqiColorHex(aqi);
    }

    function updateAqiBucket(aqi) {
        const badge = document.getElementById('aqi-bucket-badge');
        const text = document.getElementById('aqi-bucket-text');
        if (!badge || !text) return;

        const bucket = AQIMap.getAqiBucket(aqi);
        const color = getAqiColorHex(aqi);

        text.textContent = bucket;
        badge.style.background = color;
        badge.style.color = aqi <= 100 ? '#000' : '#fff';
    }

    function updatePollutants(data) {
        const mapping = {
            'val-pm25': 'pm25',
            'val-pm10': 'pm10',
            'val-no2': 'no2',
            'val-so2': 'so2',
            'val-co': 'co',
            'val-o3': 'o3',
        };

        for (const [elId, key] of Object.entries(mapping)) {
            const el = document.getElementById(elId);
            if (el) {
                el.textContent = data[key] !== null && data[key] !== undefined
                    ? data[key]
                    : '--';
            }
        }
    }

    // ── Forecast Update ─────────────────────────────────────
    function updateForecast(data, cityName) {
        document.getElementById('forecast-city-label').textContent =
            `${cityName} — Next 48 hours`;

        // Update hourly chart
        if (data.hourly_forecast) {
            AQICharts.updateForecastChart(data.hourly_forecast);
        }

        // Update summary cards
        if (data.forecast) {
            const horizonMap = { 1: '1', 6: '6', 12: '12', 24: '24', 48: '48' };
            data.forecast.forEach(fp => {
                const h = horizonMap[fp.hours_ahead];
                if (!h) return;

                const aqiEl = document.getElementById(`fc-aqi-${h}`);
                const bucketEl = document.getElementById(`fc-bucket-${h}`);
                const cardEl = document.getElementById(`fc-${h}h`);
                const weatherEl = document.getElementById(`fc-w-${h}`);

                if (aqiEl) {
                    aqiEl.textContent = Math.round(fp.predicted_aqi);
                    aqiEl.style.color = fp.aqi_color || getAqiColorHex(fp.predicted_aqi);
                }
                if (bucketEl) bucketEl.textContent = fp.aqi_bucket;
                if (cardEl) {
                    cardEl.style.borderColor = fp.aqi_color || getAqiColorHex(fp.predicted_aqi);
                }

                // Weather Injection
                if (weatherEl && fp.weather) {
                    weatherEl.innerHTML = `
                        <img src="${fp.weather.condition_icon}" alt="icon" /> 
                        ${Math.round(fp.weather.temp_c)}°C
                        <span class="rain" style="margin-left: 6px;">💧 ${fp.weather.precip_mm}mm</span>
                    `;
                } else if (weatherEl) {
                    weatherEl.innerHTML = `--°C`;
                }
            });
        }
    }

    // ── Advisory ────────────────────────────────────────────
    async function loadAdvisory(aqi, group) {
        try {
            // Find dominant pollutant from city data
            const cityData = allCities.find(c => c.city === selectedCity);
            let dominantPollutant = null;
            if (cityData) {
                const pollutants = {
                    'PM2.5': cityData.pm25,
                    'PM10': cityData.pm10,
                    'NO2': cityData.no2,
                    'SO2': cityData.so2,
                    'CO': cityData.co,
                    'O3': cityData.o3,
                };
                let maxVal = -1;
                for (const [name, val] of Object.entries(pollutants)) {
                    if (val && val > maxVal) {
                        maxVal = val;
                        dominantPollutant = name;
                    }
                }
            }

            const res = await fetch(`${API_BASE}/api/advisory`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    aqi: aqi,
                    group: group,
                    dominant_pollutant: dominantPollutant,
                }),
            });

            const data = await res.json();
            if (data.status === 'ok') {
                Advisory.render(data.advisory);
            }
        } catch (error) {
            console.error('Advisory error:', error);
        }
    }

    function onGroupChange(group) {
        if (selectedCity) {
            const cityData = allCities.find(c => c.city === selectedCity);
            const aqi = cityData ? cityData.aqi : 0;
            loadAdvisory(aqi, group);
        }
    }

    // ── Nearby Stations ──────────────────────────────────────
    function renderNearby(stations, cityName) {
        const titleEl = document.getElementById('nearby-city-name');
        if (titleEl) titleEl.textContent = cityName;

        const grid = document.getElementById('nearby-grid');
        const badge = document.getElementById('nearby-count-badge');

        if (!grid) return;

        // Filter out stations with empty or '-' AQI
        const validStations = (stations || []).filter(s => s.aqi && !isNaN(s.aqi));

        if (badge) badge.textContent = validStations.length;

        if (validStations.length === 0) {
            grid.innerHTML = `<div class="nearby-placeholder">No nearby real-time stations found within 150km.</div>`;
            return;
        }

        grid.innerHTML = validStations.map(s => {
            const color = getAqiColorHex(s.aqi);
            return `
            <div class="nearby-card" onclick="window.__selectCity && window.__selectCity('${s.city}')">
                <div class="nearby-aqi-indicator" style="background: ${color}"></div>
                <div class="nearby-card-content">
                    <div class="nearby-station-name" title="${s.name}">${s.name}</div>
                    <div class="nearby-station-city">${s.city}</div>
                    <div class="nearby-aqi-row">
                        <span class="nearby-aqi-val" style="color: ${color}">${s.aqi} AQI</span>
                        <span class="nearby-bucket">${s.bucket || '--'}</span>
                    </div>
                </div>
            </div>
            `;
        }).join('');
    }

    // ── Search ──────────────────────────────────────────────
    function setupSearch() {
        const input = document.getElementById('city-search');
        const dropdown = document.getElementById('search-dropdown');
        if (!input || !dropdown) return;

        let debounceTimer;

        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = input.value.trim().toLowerCase();
                if (query.length < 1) {
                    dropdown.classList.add('hidden');
                    return;
                }

                const matches = allCities.filter(c =>
                    c.city.toLowerCase().includes(query)
                ).slice(0, 8);

                if (matches.length === 0) {
                    dropdown.classList.add('hidden');
                    return;
                }

                dropdown.innerHTML = matches.map(c => `
                    <div class="search-item" data-city="${c.city}">
                        <span class="search-item-city">${highlightMatch(c.city, query)}</span>
                        <span class="search-item-aqi" style="background: ${getAqiColorHex(c.aqi)}">${c.aqi || 'N/A'}</span>
                    </div>
                `).join('');

                dropdown.classList.remove('hidden');

                // Click handlers
                dropdown.querySelectorAll('.search-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const city = item.dataset.city;
                        input.value = city;
                        dropdown.classList.add('hidden');
                        onCitySelect(city);
                    });
                });
            }, 200);
        });

        // Close dropdown on click outside
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        });

        // Enter key
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = input.value.trim();
                const match = allCities.find(c =>
                    c.city.toLowerCase() === query.toLowerCase()
                );
                if (match) {
                    dropdown.classList.add('hidden');
                    onCitySelect(match.city);
                }
            }
        });
    }

    function highlightMatch(text, query) {
        const idx = text.toLowerCase().indexOf(query);
        if (idx === -1) return text;
        return text.slice(0, idx) +
            `<strong>${text.slice(idx, idx + query.length)}</strong>` +
            text.slice(idx + query.length);
    }

    // ── Rankings ────────────────────────────────────────────
    function renderRankings(cities) {
        const grid = document.getElementById('rankings-grid');
        if (!grid) return;

        grid.innerHTML = cities.slice(0, 20).map((c, i) => `
            <div class="ranking-card" data-city="${c.city}">
                <span class="ranking-rank">#${i + 1}</span>
                <div class="ranking-aqi-dot" style="background: ${getAqiColorHex(c.aqi)}">
                    ${c.aqi || '?'}
                </div>
                <div class="ranking-info">
                    <div class="ranking-city">${c.city}</div>
                    <div class="ranking-bucket">${c.bucket || '--'}</div>
                </div>
            </div>
        `).join('');

        grid.querySelectorAll('.ranking-card').forEach(card => {
            card.addEventListener('click', () => {
                onCitySelect(card.dataset.city);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
    }

    // ── API Status ──────────────────────────────────────────
    function updateApiStatus(health) {
        const badge = document.getElementById('api-status');
        const text = badge.querySelector('.status-text');
        if (health && health.status === 'ok') {
            badge.classList.remove('offline');
            badge.classList.add('online');
            text.textContent = health.models_loaded ? 'AI Ready' : 'No Model';
        } else {
            badge.classList.remove('online');
            badge.classList.add('offline');
            text.textContent = 'Offline';
        }
    }

    // ── Particles ───────────────────────────────────────────
    function createParticles() {
        const container = document.getElementById('particles');
        if (!container) return;

        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDuration = (6 + Math.random() * 8) + 's';
            particle.style.animationDelay = Math.random() * 6 + 's';
            particle.style.width = (2 + Math.random() * 3) + 'px';
            particle.style.height = particle.style.width;
            container.appendChild(particle);
        }
    }

    // ── Utility ─────────────────────────────────────────────
    function getAqiColorHex(aqi) {
        if (!aqi || aqi <= 0) return '#555';
        if (aqi <= 50) return '#00e400';
        if (aqi <= 100) return '#ffff00';
        if (aqi <= 200) return '#ff7e00';
        if (aqi <= 300) return '#ff0000';
        if (aqi <= 400) return '#8f3f97';
        return '#7e0023';
    }

})();
