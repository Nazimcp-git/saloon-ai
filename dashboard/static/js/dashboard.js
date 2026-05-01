/**
 * Salon AI Dashboard — Frontend Logic
 * =====================================
 * Handles:
 *   - Auto-refreshing stats every 5 seconds
 *   - Hourly traffic chart (Chart.js)
 *   - Live clock
 *   - Counter reset
 *   - Value change animations
 */

// ── Configuration ──
const REFRESH_INTERVAL = 5000;  // ms
const API_STATS_URL = '/api/stats';
const API_RESET_URL = '/api/reset';
const API_CAPTURES_URL = '/api/captures';

// ── State ──
let hourlyChart = null;
let previousValues = {};

// ── DOM Elements ──
const elements = {
    totalToday:     document.getElementById('totalToday'),
    inStore:        document.getElementById('inStore'),
    entries:        document.getElementById('entries'),
    exits:          document.getElementById('exits'),
    statusDot:      document.getElementById('statusDot'),
    statusText:     document.getElementById('statusText'),
    clock:          document.getElementById('clock'),
    chartDate:      document.getElementById('chartDate'),
    systemStatus:   document.getElementById('systemStatus'),
    lastUpdate:     document.getElementById('lastUpdate'),
    personsInFrame: document.getElementById('personsInFrame'),
    currentDate:    document.getElementById('currentDate'),
    resetBtn:       document.getElementById('resetBtn'),
};


// ─────────────────────────────────────────────
// CLOCK
// ─────────────────────────────────────────────

function updateClock() {
    const now = new Date();
    elements.clock.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });
}

setInterval(updateClock, 1000);
updateClock();


// ─────────────────────────────────────────────
// CHART INITIALIZATION
// ─────────────────────────────────────────────

function initChart() {
    const ctx = document.getElementById('hourlyChart').getContext('2d');

    hourlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Array.from({ length: 24 }, (_, i) =>
                `${i.toString().padStart(2, '0')}:00`
            ),
            datasets: [
                {
                    label: 'Entries',
                    data: new Array(24).fill(0),
                    backgroundColor: 'rgba(6, 182, 212, 0.6)',
                    borderColor: 'rgba(6, 182, 212, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                },
                {
                    label: 'Exits',
                    data: new Array(24).fill(0),
                    backgroundColor: 'rgba(245, 158, 11, 0.4)',
                    borderColor: 'rgba(245, 158, 11, 0.8)',
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Inter', size: 11, weight: '500' },
                        boxWidth: 12,
                        padding: 16,
                    },
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    titleFont: { family: 'Inter', weight: '600' },
                    bodyFont: { family: 'Inter' },
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
                    ticks: {
                        color: '#64748b',
                        font: { family: 'Inter', size: 10 },
                        maxRotation: 0,
                        callback: function(val, index) {
                            return index % 3 === 0 ? this.getLabelForValue(val) : '';
                        }
                    },
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
                    ticks: {
                        color: '#64748b',
                        font: { family: 'Inter', size: 10 },
                        stepSize: 1,
                    },
                },
            },
        },
    });
}


// ─────────────────────────────────────────────
// DATA FETCHING
// ─────────────────────────────────────────────

async function fetchStats() {
    try {
        const response = await fetch(API_STATS_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        updateDashboard(data);
        setStatus(true);

    } catch (error) {
        console.error('Failed to fetch stats:', error);
        setStatus(false);
    }
}

async function fetchCaptures() {
    try {
        const dateInput = document.getElementById('captureDateFilter');
        const dateVal = dateInput ? dateInput.value : '';
        const url = dateVal ? `${API_CAPTURES_URL}?date=${dateVal}` : API_CAPTURES_URL;
        
        const response = await fetch(url);
        if (!response.ok) return;
        
        const data = await response.json();
        const grid = document.getElementById('capturesGrid');
        if (!grid) return;
        
        grid.innerHTML = ''; // Clear current
        
        if (data.length === 0) {
            grid.innerHTML = '<p style="color: #64748b;">No recent captures.</p>';
            return;
        }
        
        data.forEach(capture => {
            const date = new Date(capture.time * 1000);
            const timeStr = date.toLocaleTimeString();
            
            const card = document.createElement('div');
            card.style.cssText = 'background: #1e293b; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid rgba(255,255,255,0.05);';
            
            card.innerHTML = `
                <div style="height: 140px; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #000;">
                    <img src="${capture.url}" alt="Capture" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
                <div style="padding: 0.5rem; text-align: center; color: #94a3b8; font-size: 0.8rem;">
                    Captured at ${timeStr}
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (error) {
        console.error('Failed to fetch captures:', error);
    }
}


// ─────────────────────────────────────────────
// UI UPDATES
// ─────────────────────────────────────────────

function updateDashboard(data) {
    const live = data.live || {};

    // Update stat cards with animation
    animateValue('totalToday', live.total_customers || data.today_total || live.entered || 0);
    animateValue('inStore', live.inside || 0);
    animateValue('entries', live.entered || 0);
    animateValue('exits', live.exited || 0);

    // Update info panel
    elements.systemStatus.textContent = live.last_updated ? 'Running' : 'Idle';
    elements.personsInFrame.textContent = live.persons_in_frame || 0;
    elements.currentDate.textContent = data.date || '—';

    if (live.last_updated) {
        const t = new Date(live.last_updated);
        elements.lastUpdate.textContent = t.toLocaleTimeString();
    }

    // Update chart
    if (data.hourly && hourlyChart) {
        hourlyChart.data.datasets[0].data = data.hourly.entered;
        hourlyChart.data.datasets[1].data = data.hourly.exited;
        hourlyChart.update('none'); // No animation for smoother updates
    }

    elements.chartDate.textContent = data.date || '';
}

function animateValue(elementId, newValue) {
    const el = elements[elementId];
    if (!el) return;

    const oldValue = previousValues[elementId];
    el.textContent = newValue;

    if (oldValue !== undefined && oldValue !== newValue) {
        el.classList.remove('value-updated');
        void el.offsetWidth; // Force reflow for re-animation
        el.classList.add('value-updated');
    }

    previousValues[elementId] = newValue;
}

function setStatus(online) {
    if (online) {
        elements.statusDot.classList.add('active');
        elements.statusText.textContent = 'Connected';
    } else {
        elements.statusDot.classList.remove('active');
        elements.statusText.textContent = 'Disconnected';
    }
}


// ─────────────────────────────────────────────
// RESET BUTTON
// ─────────────────────────────────────────────

elements.resetBtn.addEventListener('click', async () => {
    if (!confirm('Reset all counters for today?')) return;

    try {
        const response = await fetch(API_RESET_URL, { method: 'POST' });
        if (response.ok) {
            fetchStats(); // Refresh immediately
        }
    } catch (error) {
        console.error('Reset failed:', error);
    }
});


// ─────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const captureDateFilter = document.getElementById('captureDateFilter');
    if (captureDateFilter) {
        const todayStr = new Date().toISOString().split('T')[0];
        captureDateFilter.value = todayStr;
        captureDateFilter.addEventListener('change', fetchCaptures);
    }

    initChart();
    fetchStats();
    fetchCaptures();
    setInterval(() => {
        fetchStats();
        fetchCaptures();
    }, REFRESH_INTERVAL);
});
