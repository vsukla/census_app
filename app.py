from flask import Flask, render_template, jsonify, request
import requests
from functools import lru_cache
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from flask_talisman import Talisman
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Debug environment variables
logger.info("Environment variables:")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f".env file exists: {os.path.exists('.env')}")
logger.info(f"CENSUS_API_KEY length: {len(os.getenv('CENSUS_API_KEY', ''))}")

app = Flask(__name__)

# Configure Content Security Policy
csp = {
    'default-src': "'self'",
    'img-src': ["'self'", 'data:'],
    'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://cdn.jsdelivr.net"],
    'style-src': ["'self'", "'unsafe-inline'"],
}

# Initialize Talisman with security headers
talisman = Talisman(
    app,
    force_https=False,  # Disable HTTPS forcing for development
    strict_transport_security=False,  # Disable HSTS for development
    session_cookie_secure=False,  # Disable secure cookies for development
    content_security_policy=csp,
    feature_policy={
        'geolocation': "'none'",
        'microphone': "'none'",
        'camera': "'none'"
    }
)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Add security headers to all responses
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Census API configuration
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY', 'fb7093b063c3f9e8edead5e521875ec92fa40f11')
CENSUS_API_BASE_URL = "https://api.census.gov/data/2020/acs/acs5"  # Changed to ACS5 endpoint

logger.info(f"Using Census API Key: {CENSUS_API_KEY[:5]}...")

@lru_cache(maxsize=50)
def get_state_data(state_code):
    """Fetch and cache state demographic data from Census API"""
    try:
        if not CENSUS_API_KEY:
            return {"error": "Please check your Census API key configuration"}, 400

        # Test API connection with a simple query first
        test_url = f"{CENSUS_API_BASE_URL}?get=NAME&for=state:{state_code}&key={CENSUS_API_KEY}"
        logger.debug(f"Testing API connection with URL: {test_url}")
        test_response = requests.get(test_url)
        
        if test_response.status_code == 403:
            logger.error(f"API Key error. Status code: {test_response.status_code}")
            logger.error(f"Response: {test_response.text}")
            return {"error": "Please check your Census API key configuration"}, 400
        
        if test_response.status_code != 200:
            logger.error(f"API request failed. Status code: {test_response.status_code}")
            logger.error(f"Response: {test_response.text}")
            return {"error": f"API request failed with status code {test_response.status_code}"}, 400

        # Total population (B01003_001E)
        total_pop_url = f"{CENSUS_API_BASE_URL}?get=B01003_001E&for=state:{state_code}&key={CENSUS_API_KEY}"
        logger.debug(f"Fetching total population from: {total_pop_url}")
        total_pop_response = requests.get(total_pop_url)
        
        if total_pop_response.status_code != 200:
            logger.error(f"Population data request failed. Status code: {total_pop_response.status_code}")
            logger.error(f"Response: {total_pop_response.text}")
            return {"error": f"Failed to fetch population data"}, 400
            
        total_pop_data = total_pop_response.json()
        total_population = int(total_pop_data[1][0])
        logger.debug(f"Total population for state {state_code}: {total_population}")

        # Race distribution (using ACS estimates)
        race_url = f"{CENSUS_API_BASE_URL}?get=B02001_002E,B02001_003E,B02001_004E,B02001_005E,B02001_006E&for=state:{state_code}&key={CENSUS_API_KEY}"
        logger.debug(f"Fetching race distribution from: {race_url}")
        race_response = requests.get(race_url)
        
        if race_response.status_code != 200:
            logger.error(f"Race data request failed. Status code: {race_response.status_code}")
            return {"error": f"Failed to fetch race data"}, 400
            
        race_data = race_response.json()
        
        race_distribution = {
            "White": int(race_data[1][0]),
            "Black": int(race_data[1][1]),
            "American Indian": int(race_data[1][2]),
            "Asian": int(race_data[1][3]),
            "Other": int(race_data[1][4])
        }
        logger.debug(f"Race distribution for state {state_code}: {race_distribution}")

        # Hispanic/Latino ethnicity (B03003)
        ethnicity_url = f"{CENSUS_API_BASE_URL}?get=B03003_002E,B03003_003E&for=state:{state_code}&key={CENSUS_API_KEY}"
        ethnicity_response = requests.get(ethnicity_url)
        
        if ethnicity_response.status_code != 200:
            logger.error(f"Ethnicity data request failed. Status code: {ethnicity_response.status_code}")
            return {"error": f"Failed to fetch ethnicity data"}, 400
            
        ethnicity_data = ethnicity_response.json()
        
        total = int(ethnicity_data[1][0]) + int(ethnicity_data[1][1])
        ethnicity_distribution = {
            "Hispanic": round((int(ethnicity_data[1][0]) / total) * 100, 1),
            "Non-Hispanic": round((int(ethnicity_data[1][1]) / total) * 100, 1)
        }

        # Voting age population (B05003_001E)
        voting_age_url = f"{CENSUS_API_BASE_URL}?get=B05003_001E&for=state:{state_code}&key={CENSUS_API_KEY}"
        voting_age_response = requests.get(voting_age_url)
        
        if voting_age_response.status_code != 200:
            logger.error(f"Voting age data request failed. Status code: {voting_age_response.status_code}")
            return {"error": f"Failed to fetch voting age data"}, 400
            
        voting_age_data = voting_age_response.json()
        voting_age_population = int(voting_age_data[1][0])

        # Median age (B01002_001E)
        median_age_url = f"{CENSUS_API_BASE_URL}?get=B01002_001E&for=state:{state_code}&key={CENSUS_API_KEY}"
        median_age_response = requests.get(median_age_url)
        
        if median_age_response.status_code != 200:
            logger.error(f"Median age data request failed. Status code: {median_age_response.status_code}")
            return {"error": f"Failed to fetch median age data"}, 400
            
        median_age_data = median_age_response.json()
        median_age = float(median_age_data[1][0])

        # Population density calculation
        state_areas = {
            "01": 52420, "02": 665384, "04": 113990, "05": 53179, "06": 163696,
            "08": 104094, "09": 5543, "10": 1982, "12": 65758, "13": 59425,
            "15": 10932, "16": 83569, "17": 57914, "18": 36420, "19": 56273,
            "20": 82278, "21": 40408, "22": 52378, "23": 35380, "24": 12407,
            "25": 10554, "26": 96714, "27": 86936, "28": 48432, "29": 69707,
            "30": 147040, "31": 77348, "32": 110572, "33": 9349, "34": 8722,
            "35": 121590, "36": 54555, "37": 53819, "38": 70698, "39": 44826,
            "40": 69899, "41": 98379, "42": 46054, "44": 1545, "45": 32020,
            "46": 77116, "47": 42144, "48": 268597, "49": 84897, "50": 9616,
            "51": 42775, "53": 71298, "54": 24230, "55": 65496, "56": 97813
        }
        
        population_density = total_population / state_areas.get(state_code, 1)

        # Historical population trends (simulated data for demonstration)
        current_year = datetime.now().year
        years = list(range(current_year - 10, current_year + 1))
        base_population = total_population * 0.9
        growth_rate = 0.01
        population_growth = [
            int(base_population * (1 + growth_rate) ** (year - (current_year - 10)))
            for year in years
        ]

        return {
            "total_population": total_population,
            "race_distribution": race_distribution,
            "ethnicity_distribution": ethnicity_distribution,
            "voting_age_population": voting_age_population,
            "median_age": median_age,
            "population_density": population_density,
            "trends": {
                "years": years,
                "population_growth": population_growth
            }
        }

    except Exception as e:
        logger.error(f"Request exception: {str(e)}")
        return {"error": f"API request failed: {str(e)}"}, 500

@app.route('/')
def index():
    # List of US states with their FIPS codes
    states = [
        {"code": "01", "name": "Alabama"}, {"code": "02", "name": "Alaska"},
        {"code": "04", "name": "Arizona"}, {"code": "05", "name": "Arkansas"},
        {"code": "06", "name": "California"}, {"code": "08", "name": "Colorado"},
        {"code": "09", "name": "Connecticut"}, {"code": "10", "name": "Delaware"},
        {"code": "12", "name": "Florida"}, {"code": "13", "name": "Georgia"},
        {"code": "15", "name": "Hawaii"}, {"code": "16", "name": "Idaho"},
        {"code": "17", "name": "Illinois"}, {"code": "18", "name": "Indiana"},
        {"code": "19", "name": "Iowa"}, {"code": "20", "name": "Kansas"},
        {"code": "21", "name": "Kentucky"}, {"code": "22", "name": "Louisiana"},
        {"code": "23", "name": "Maine"}, {"code": "24", "name": "Maryland"},
        {"code": "25", "name": "Massachusetts"}, {"code": "26", "name": "Michigan"},
        {"code": "27", "name": "Minnesota"}, {"code": "28", "name": "Mississippi"},
        {"code": "29", "name": "Missouri"}, {"code": "30", "name": "Montana"},
        {"code": "31", "name": "Nebraska"}, {"code": "32", "name": "Nevada"},
        {"code": "33", "name": "New Hampshire"}, {"code": "34", "name": "New Jersey"},
        {"code": "35", "name": "New Mexico"}, {"code": "36", "name": "New York"},
        {"code": "37", "name": "North Carolina"}, {"code": "38", "name": "North Dakota"},
        {"code": "39", "name": "Ohio"}, {"code": "40", "name": "Oklahoma"},
        {"code": "41", "name": "Oregon"}, {"code": "42", "name": "Pennsylvania"},
        {"code": "44", "name": "Rhode Island"}, {"code": "45", "name": "South Carolina"},
        {"code": "46", "name": "South Dakota"}, {"code": "47", "name": "Tennessee"},
        {"code": "48", "name": "Texas"}, {"code": "49", "name": "Utah"},
        {"code": "50", "name": "Vermont"}, {"code": "51", "name": "Virginia"},
        {"code": "53", "name": "Washington"}, {"code": "54", "name": "West Virginia"},
        {"code": "55", "name": "Wisconsin"}, {"code": "56", "name": "Wyoming"}
    ]
    return render_template('index.html', states=states)

@app.route('/api/state/<state_code>')
def get_state_api(state_code):
    """API endpoint to get state demographic data"""
    try:
        # Validate state code format
        if not re.match(r'^[0-9]{2}$', state_code):
            return jsonify({"error": "Invalid state code format"}), 400

        data = get_state_data(state_code)
        
        if "error" in data:
            logger.error(f"Error fetching data for state {state_code}: {data['error']}")
            return jsonify(data), 400
            
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True) 