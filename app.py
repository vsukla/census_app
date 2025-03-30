from flask import Flask, render_template, jsonify, request
import requests
from functools import lru_cache
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from flask_cors import CORS
import re

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
app.config['DEBUG'] = True

# Initialize CORS
CORS(app)

@app.before_request
def log_request_info():
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('Method: %s', request.method)
    logger.debug('Path: %s', request.path)

@app.errorhandler(403)
def forbidden_error(error):
    logger.error('403 error: %s', error)
    return jsonify({
        'error': 'Forbidden',
        'message': str(error),
        'status_code': 403
    }), 403

@app.errorhandler(500)
def internal_error(error):
    logger.error('500 error: %s', error)
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error),
        'status_code': 500
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    logger.error('Unhandled exception: %s', error)
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error),
        'status_code': 500
    }), 500

# Census API configuration
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY')
if not CENSUS_API_KEY:
    logger.error("CENSUS_API_KEY environment variable is not set")
    raise ValueError("CENSUS_API_KEY environment variable is required")

CENSUS_API_BASE_URL = "https://api.census.gov/data/2020/acs/acs5"

logger.info(f"Using Census API Key: {CENSUS_API_KEY[:5]}...")

@lru_cache(maxsize=50)
def get_state_data(state_code):
    """Fetch and cache state demographic data from Census API"""
    try:
        # Test API connection with a simple query first
        test_url = f"{CENSUS_API_BASE_URL}?get=NAME&for=state:{state_code}&key={CENSUS_API_KEY}"
        logger.debug(f"Testing API connection with URL: {test_url}")
        
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        test_response = requests.get(test_url, headers=headers, allow_redirects=True)
        
        # Log the full response for debugging
        logger.debug(f"Test response status: {test_response.status_code}")
        logger.debug(f"Test response headers: {dict(test_response.headers)}")
        logger.debug(f"Test response content: {test_response.text[:500]}")  # First 500 chars
        
        if test_response.status_code == 403:
            logger.error(f"API Key error. Status code: {test_response.status_code}")
            logger.error(f"Response: {test_response.text}")
            return {"error": "Invalid Census API key. Please check your configuration."}, 400
        
        if test_response.status_code != 200:
            logger.error(f"API request failed. Status code: {test_response.status_code}")
            logger.error(f"Response: {test_response.text}")
            return {"error": f"API request failed with status code {test_response.status_code}"}, 400

        # Parse the test response
        try:
            test_data = test_response.json()
            if not isinstance(test_data, list) or len(test_data) < 2:
                logger.error(f"Invalid response format: {test_data}")
                return {"error": "Invalid response format from Census API"}, 400
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {test_response.text}")
            return {"error": "Failed to parse Census API response"}, 400

        # Total population (B01003_001E)
        total_pop_url = f"{CENSUS_API_BASE_URL}?get=B01003_001E&for=state:{state_code}&key={CENSUS_API_KEY}"
        logger.debug(f"Fetching total population from: {total_pop_url}")
        total_pop_response = requests.get(total_pop_url, headers=headers, allow_redirects=True)
        
        # Log the full response for debugging
        logger.debug(f"Total pop response status: {total_pop_response.status_code}")
        logger.debug(f"Total pop response headers: {dict(total_pop_response.headers)}")
        logger.debug(f"Total pop response content: {total_pop_response.text[:500]}")  # First 500 chars
        
        if total_pop_response.status_code != 200:
            logger.error(f"Population data request failed. Status code: {total_pop_response.status_code}")
            logger.error(f"Response: {total_pop_response.text}")
            return {"error": f"Failed to fetch population data"}, 400
            
        try:
            total_pop_data = total_pop_response.json()
            if not isinstance(total_pop_data, list) or len(total_pop_data) < 2:
                logger.error(f"Invalid population data format: {total_pop_data}")
                return {"error": "Invalid population data format from Census API"}, 400
            total_population = int(total_pop_data[1][0])
            logger.debug(f"Total population for state {state_code}: {total_population}")
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse population data: {e}")
            logger.error(f"Response content: {total_pop_response.text}")
            return {"error": "Failed to parse population data"}, 400

        # Race distribution (using ACS estimates)
        race_url = f"{CENSUS_API_BASE_URL}?get=B02001_002E,B02001_003E,B02001_004E,B02001_005E,B02001_006E&for=state:{state_code}&key={CENSUS_API_KEY}"
        logger.debug(f"Fetching race distribution from: {race_url}")
        race_response = requests.get(race_url, headers=headers, allow_redirects=True)
        
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
        ethnicity_response = requests.get(ethnicity_url, headers=headers, allow_redirects=True)
        
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
        voting_age_response = requests.get(voting_age_url, headers=headers, allow_redirects=True)
        
        if voting_age_response.status_code != 200:
            logger.error(f"Voting age data request failed. Status code: {voting_age_response.status_code}")
            return {"error": f"Failed to fetch voting age data"}, 400
            
        voting_age_data = voting_age_response.json()
        voting_age_population = int(voting_age_data[1][0])

        # Median age (B01002_001E)
        median_age_url = f"{CENSUS_API_BASE_URL}?get=B01002_001E&for=state:{state_code}&key={CENSUS_API_KEY}"
        median_age_response = requests.get(median_age_url, headers=headers, allow_redirects=True)
        
        if median_age_response.status_code != 200:
            logger.error(f"Median age data request failed. Status code: {median_age_response.status_code}")
            return {"error": f"Failed to fetch median age data"}, 400
            
        median_age_data = median_age_response.json()
        median_age = float(median_age_data[1][0])

        # Return combined data
        return {
            "state_code": state_code,
            "state_name": test_data[1][0],
            "total_population": total_population,
            "race_distribution": race_distribution,
            "ethnicity_distribution": ethnicity_distribution,
            "voting_age_population": voting_age_population,
            "median_age": median_age
        }

    except Exception as e:
        logger.error(f"Error fetching data for state {state_code}: {str(e)}")
        return {"error": f"Failed to fetch data: {str(e)}"}, 500

@app.route('/')
def index():
    """Render the main page"""
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

@app.route('/api/state/<state_code>', methods=['GET'])
def get_state_api(state_code):
    """API endpoint to get state demographic data"""
    try:
        logger.debug(f"Received request for state code: {state_code}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request method: {request.method}")
        
        # Validate state code format
        if not re.match(r'^[0-9]{2}$', state_code):
            logger.error(f"Invalid state code format: {state_code}")
            return jsonify({"error": "Invalid state code format"}), 400

        data = get_state_data(state_code)
        
        if isinstance(data, tuple) and len(data) == 2:
            logger.error(f"Error fetching data for state {state_code}: {data[0]}")
            return jsonify(data[0]), data[1]
            
        logger.debug(f"Successfully fetched data for state {state_code}")
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 