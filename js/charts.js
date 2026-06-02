/**
 * Charts Module — Chart.js forecast and historical AQI visualizations
 */

const AQICharts = (() => {
    let forecastChart = null;
    let historyChart = null;

    // Common chart defaults for dark theme
    const DARK_THEME = {
        color: '#94a3b8',
        borderColor: 'rgba(255,255,255,0.08)',
        fontFamily: "'Inter', sans-serif",
    };

    // AQI threshold lines
    const AQI_THRESHOLDS = [
        { value: 50, label: 'Good', color: 'rgba(0,228,0,0.3)' },
        { value: 100, label: 'Satisfactory', color: 'rgba(255,255,0,0.3)' },
        { value: 200, label: 'Moderate', color: 'rgba(255,126,0,0.3)' },
        { value: 300, label: 'Poor', color: 'rgba(255,0,0,0.3)' },
        { value: 400, label: 'Very Poor', color: 'rgba(143,63,151,0.3)' },
    ];

    function getGradient(ctx, chartArea, color1, color2) {
        const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    }

    function initForecastChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (forecastChart) forecastChart.destroy();

        forecastChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Predicted AQI',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#3b82f6',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        titleFont: { family: DARK_THEME.fontFamily, weight: '600' },
                        bodyFont: { family: DARK_THEME.fontFamily },
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            title: (items) => `Hour +${items[0].label}`,
                            label: (item) => {
                                const aqi = item.parsed.y;
                                const bucket = getBucketLabel(aqi);
                                return `AQI: ${Math.round(aqi)} (${bucket})`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: DARK_THEME.borderColor, drawBorder: false },
                        ticks: {
                            color: DARK_THEME.color,
                            font: { family: DARK_THEME.fontFamily, size: 11 },
                            maxTicksLimit: 12,
                            callback: (val, idx) => idx % 6 === 0 ? `+${val}h` : '',
                        },
                        title: {
                            display: true,
                            text: 'Hours Ahead',
                            color: DARK_THEME.color,
                            font: { family: DARK_THEME.fontFamily, size: 12 },
                        },
                    },
                    y: {
                        grid: { color: DARK_THEME.borderColor, drawBorder: false },
                        ticks: {
                            color: DARK_THEME.color,
                            font: { family: DARK_THEME.fontFamily, size: 11 },
                        },
                        title: {
                            display: true,
                            text: 'AQI',
                            color: DARK_THEME.color,
                            font: { family: DARK_THEME.fontFamily, size: 12 },
                        },
                        min: 0,
                    },
                },
            },
        });

        return forecastChart;
    }

    function updateForecastChart(hourlyData) {
        if (!forecastChart || !hourlyData || hourlyData.length === 0) return;

        const labels = hourlyData.map(d => d.hour);
        const values = hourlyData.map(d => d.aqi);
        const colors = hourlyData.map(d => d.color || '#3b82f6');

        forecastChart.data.labels = labels;
        forecastChart.data.datasets[0].data = values;

        // Dynamic gradient based on AQI range
        forecastChart.data.datasets[0].backgroundColor = function (context) {
            const chart = context.chart;
            const { ctx, chartArea } = chart;
            if (!chartArea) return 'rgba(59, 130, 246, 0.1)';
            return getGradient(ctx, chartArea, 'rgba(59, 130, 246, 0.02)', 'rgba(59, 130, 246, 0.2)');
        };

        // Add AQI threshold annotations
        const maxAqi = Math.max(...values, 100);
        forecastChart.options.scales.y.max = Math.ceil(maxAqi / 50) * 50 + 50;

        forecastChart.update('none');
    }

    function initHistoryChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (historyChart) historyChart.destroy();

        historyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Daily AQI',
                    data: [],
                    backgroundColor: [],
                    borderColor: [],
                    borderWidth: 1,
                    borderRadius: 3,
                    barPercentage: 0.8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        titleFont: { family: DARK_THEME.fontFamily, weight: '600' },
                        bodyFont: { family: DARK_THEME.fontFamily },
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: (item) => {
                                const aqi = item.parsed.y;
                                const bucket = getBucketLabel(aqi);
                                return `AQI: ${Math.round(aqi)} (${bucket})`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: DARK_THEME.color,
                            font: { family: DARK_THEME.fontFamily, size: 10 },
                            maxTicksLimit: 15,
                            maxRotation: 45,
                        },
                    },
                    y: {
                        grid: { color: DARK_THEME.borderColor, drawBorder: false },
                        ticks: {
                            color: DARK_THEME.color,
                            font: { family: DARK_THEME.fontFamily, size: 11 },
                        },
                        title: {
                            display: true,
                            text: 'AQI',
                            color: DARK_THEME.color,
                            font: { family: DARK_THEME.fontFamily, size: 12 },
                        },
                        min: 0,
                    },
                },
            },
        });

        return historyChart;
    }

    function updateHistoryChart(historyData) {
        if (!historyChart || !historyData || historyData.length === 0) return;

        const labels = historyData.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
        });
        const values = historyData.map(d => d.aqi);
        const bgColors = values.map(aqi => getAqiColor(aqi, 0.7));
        const borderColors = values.map(aqi => getAqiColor(aqi, 1));

        historyChart.data.labels = labels;
        historyChart.data.datasets[0].data = values;
        historyChart.data.datasets[0].backgroundColor = bgColors;
        historyChart.data.datasets[0].borderColor = borderColors;

        historyChart.update('none');
    }

    function getAqiColor(aqi, alpha = 1) {
        let r, g, b;
        if (aqi <= 50) { r = 0; g = 228; b = 0; }
        else if (aqi <= 100) { r = 255; g = 255; b = 0; }
        else if (aqi <= 200) { r = 255; g = 126; b = 0; }
        else if (aqi <= 300) { r = 255; g = 0; b = 0; }
        else if (aqi <= 400) { r = 143; g = 63; b = 151; }
        else { r = 126; g = 0; b = 35; }
        return `rgba(${r},${g},${b},${alpha})`;
    }

    function getBucketLabel(aqi) {
        if (aqi <= 50) return 'Good';
        if (aqi <= 100) return 'Satisfactory';
        if (aqi <= 200) return 'Moderate';
        if (aqi <= 300) return 'Poor';
        if (aqi <= 400) return 'Very Poor';
        return 'Severe';
    }

    return {
        initForecastChart,
        updateForecastChart,
        initHistoryChart,
        updateHistoryChart,
        getAqiColor,
        getBucketLabel,
    };
})();
