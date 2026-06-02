/**
 * Advisory Module — Health advisory panel rendering
 */

const Advisory = (() => {
    let currentAqi = null;
    let currentGroup = 'general';
    let currentCity = null;

    function init(onGroupChange) {
        const select = document.getElementById('user-group-select');
        if (select) {
            select.addEventListener('change', (e) => {
                currentGroup = e.target.value;
                if (currentAqi !== null && onGroupChange) {
                    onGroupChange(currentGroup);
                }
            });
        }
    }

    function render(advisoryData) {
        const container = document.getElementById('advisory-content');
        if (!container || !advisoryData) return;

        currentAqi = advisoryData.aqi;

        const maskLabels = {
            'not_needed': '✅ Not Needed',
            'recommended': '😷 Recommended',
            'recommended_sensitive': '😷 For Sensitive Groups',
            'N95_recommended': '😷 N95 Recommended',
            'N95_essential': '🔴 N95 Essential',
        };

        const activityLabels = {
            'safe': '✅ Safe',
            'limit_prolonged': '⚠️ Limit Prolonged',
            'avoid': '🚫 Avoid',
            'dangerous': '☠️ Dangerous',
            'emergency': '🚨 Emergency',
        };

        let html = `<div class="advisory-main fade-in">`;

        // Summary Card
        html += `
            <div class="advisory-summary-card" style="border-color: ${advisoryData.bucket_color}">
                <div class="advisory-summary-text" style="color: ${advisoryData.bucket_color}">
                    ${advisoryData.bucket_emoji} ${advisoryData.summary}
                </div>
            </div>
        `;

        // Meta items
        html += `<div class="advisory-meta">`;
        html += `
            <div class="advisory-meta-item">
                <span class="advisory-meta-icon">🏃</span>
                <div>
                    <span class="advisory-meta-label">Outdoor Activity</span>
                    <span class="advisory-meta-value">${activityLabels[advisoryData.outdoor_activity] || advisoryData.outdoor_activity}</span>
                </div>
            </div>
        `;
        html += `
            <div class="advisory-meta-item">
                <span class="advisory-meta-icon">😷</span>
                <div>
                    <span class="advisory-meta-label">Mask</span>
                    <span class="advisory-meta-value">${maskLabels[advisoryData.mask_recommendation] || advisoryData.mask_recommendation}</span>
                </div>
            </div>
        `;
        if (advisoryData.ventilation) {
            html += `
                <div class="advisory-meta-item">
                    <span class="advisory-meta-icon">🪟</span>
                    <div>
                        <span class="advisory-meta-label">Ventilation</span>
                        <span class="advisory-meta-value">${advisoryData.ventilation}</span>
                    </div>
                </div>
            `;
        }
        html += `</div>`;

        // Tips
        if (advisoryData.tips && advisoryData.tips.length > 0) {
            html += `
                <div class="advisory-tips">
                    <div class="advisory-tips-title">💡 Recommendations</div>
                    ${advisoryData.tips.map(tip => `
                        <div class="advisory-tip">
                            <span class="tip-bullet">›</span>
                            <span>${tip}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // Pollutant info
        if (advisoryData.dominant_pollutant && advisoryData.pollutant_advice) {
            const pa = advisoryData.pollutant_advice;
            html += `
                <div class="pollutant-info">
                    <div class="pollutant-info-title">🔬 Dominant Pollutant: ${advisoryData.dominant_pollutant}</div>
                    <p><strong>What:</strong> ${pa.description}</p>
                    <p><strong>Sources:</strong> ${pa.sources}</p>
                    <p><strong>Protection:</strong> ${pa.protection}</p>
                </div>
            `;
        }

        html += `</div>`;
        container.innerHTML = html;
    }

    function getGroup() {
        return currentGroup;
    }

    function clear() {
        const container = document.getElementById('advisory-content');
        if (container) {
            container.innerHTML = `
                <div class="advisory-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
                    </svg>
                    <p>Select a city to receive personalized health recommendations</p>
                </div>
            `;
        }
        currentAqi = null;
    }

    return { init, render, getGroup, clear };
})();
