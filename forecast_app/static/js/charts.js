/* forecast_app/static/js/charts.js */
// Chart.js configuration for Onion Price Forecast

let priceChart = null;
let predictionChart = null;

// Initialize price chart
function initPriceChart(data) {
    const ctx = document.getElementById('priceChart');
    if (!ctx) return;
    
    const labels = data.map(item => item.date);
    const prices = data.map(item => item.price);
    
    if (priceChart) {
        priceChart.destroy();
    }
    
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Onion Price (₹/quintal)',
                data: prices,
                borderColor: '#e67e22',
                backgroundColor: 'rgba(230, 126, 34, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#d35400',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `Price: ₹${context.parsed.y.toLocaleString('en-IN')}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Price (₹)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                }
            }
        }
    });
}

// Initialize prediction chart
function initPredictionChart(data) {
    const ctx = document.getElementById('predictionChart');
    if (!ctx) return;
    
    const labels = data.map(item => item.date);
    const predicted = data.map(item => item.predicted);
    const lower = data.map(item => item.lower);
    const upper = data.map(item => item.upper);
    
    if (predictionChart) {
        predictionChart.destroy();
    }
    
    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Predicted Price',
                    data: predicted,
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Confidence Interval',
                    data: upper,
                    borderColor: 'rgba(39, 174, 96, 0.3)',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    borderWidth: 1,
                    fill: '+1',
                    tension: 0.4
                },
                {
                    label: 'Lower Bound',
                    data: lower,
                    borderColor: 'rgba(39, 174, 96, 0.3)',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    borderWidth: 1,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Predicted Price (₹)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    });
}

// Load price data from API
async function loadPriceData(days = 30) {
    try {
        const response = await fetch(`/api/prices/?days=${days}`);
        const data = await response.json();
        
        if (data.data && data.data.length > 0) {
            const chartData = data.data.map(item => ({
                date: item.date,
                price: item.modal_price
            }));
            initPriceChart(chartData);
        }
    } catch (error) {
        console.error('Error loading price data:', error);
    }
}

// Load prediction data from API
async function loadPredictionData() {
    try {
        const response = await fetch('/api/predict/');
        const data = await response.json();
        
        if (data.predictions && data.predictions.length > 0) {
            const chartData = data.predictions.map(item => ({
                date: item.date,
                predicted: item.predicted_price,
                lower: item.lower_bound,
                upper: item.upper_bound
            }));
            initPredictionChart(chartData);
        }
    } catch (error) {
        console.error('Error loading prediction data:', error);
    }
}

// Initialize charts when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Load price chart if element exists
    if (document.getElementById('priceChart')) {
        loadPriceData(30);
    }
    
    // Load prediction chart if element exists
    if (document.getElementById('predictionChart')) {
        loadPredictionData();
    }
    
    // Update data every 5 minutes
    setInterval(() => {
        if (document.getElementById('priceChart')) {
            loadPriceData(30);
        }
    }, 300000);
});

// Export functions for use in templates
window.onionCharts = {
    initPriceChart,
    initPredictionChart,
    loadPriceData,
    loadPredictionData
};