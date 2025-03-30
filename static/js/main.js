document.addEventListener('DOMContentLoaded', function() {
    const stateSelect = document.getElementById('state');
    let raceChart = null;
    let ethnicityChart = null;
    let trendsChart = null;

    stateSelect.addEventListener('change', async function() {
        const stateCode = this.value;
        if (!stateCode) {
            clearCharts();
            return;
        }

        try {
            const response = await fetch(`/api/state/${stateCode}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            updateDemographicsCard(data);
            updateRaceChart(data);
            updateEthnicityChart(data);
            updateTrendsChart(data);
        } catch (error) {
            console.error('Error fetching data:', error);
            alert('Error fetching data. Please try again.');
        }
    });

    function clearCharts() {
        if (raceChart) raceChart.destroy();
        if (ethnicityChart) ethnicityChart.destroy();
        if (trendsChart) trendsChart.destroy();
        
        document.querySelector('#demographics-card .data-display').innerHTML = 
            '<p>Select a state to view demographic data</p>';
    }

    function updateDemographicsCard(data) {
        const demographicsCard = document.querySelector('#demographics-card .data-display');
        demographicsCard.innerHTML = `
            <div class="demographics-grid">
                <div class="demographic-item">
                    <h3>Total Population</h3>
                    <p>${data.total_population.toLocaleString()}</p>
                </div>
                <div class="demographic-item">
                    <h3>Voting Age Population</h3>
                    <p>${data.voting_age_population.toLocaleString()}</p>
                </div>
                <div class="demographic-item">
                    <h3>Median Age</h3>
                    <p>${data.median_age}</p>
                </div>
            </div>
        `;
    }

    function updateRaceChart(data) {
        const ctx = document.getElementById('raceChart');
        if (raceChart) raceChart.destroy();

        raceChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: Object.keys(data.race_distribution),
                datasets: [{
                    data: Object.values(data.race_distribution),
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }

    function updateEthnicityChart(data) {
        const ctx = document.getElementById('ethnicityChart');
        if (ethnicityChart) ethnicityChart.destroy();

        ethnicityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(data.ethnicity_distribution),
                datasets: [{
                    label: 'Percentage',
                    data: Object.values(data.ethnicity_distribution),
                    backgroundColor: '#36A2EB'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }

    function updateTrendsChart(data) {
        const ctx = document.getElementById('trendsChart');
        if (trendsChart) trendsChart.destroy();

        trendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.trends.years,
                datasets: [{
                    label: 'Population Growth',
                    data: data.trends.population_growth,
                    borderColor: '#FF6384',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}); 