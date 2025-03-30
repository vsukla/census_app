document.addEventListener('DOMContentLoaded', function() {
    const stateSelect = document.getElementById('state');
    let raceChart = null;
    let ethnicityChart = null;

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
        } catch (error) {
            console.error('Error fetching data:', error);
            const demographicsCard = document.querySelector('#demographics-card .data-display');
            demographicsCard.innerHTML = `
                <div class="error-message">
                    <h3>Error Loading Data</h3>
                    <p>${error.message}</p>
                    <p>Please check your Census API key configuration.</p>
                </div>
            `;
            clearCharts();
        }
    });

    function clearCharts() {
        if (raceChart) raceChart.destroy();
        if (ethnicityChart) ethnicityChart.destroy();
        
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
            type: 'pie',
            data: {
                labels: Object.keys(data.ethnicity_distribution),
                datasets: [{
                    data: Object.values(data.ethnicity_distribution),
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB'
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
}); 