# Flask and extensions
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Standard library
import json
import logging
import os
import re
import requests
import argparse
from functools import lru_cache

# Third-party
from dotenv import load_dotenv

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
        # Combine all variables into a single API call
        variables = [
            'NAME',                    # State name
            'B01003_001E',            # Total population
            'B02001_002E',            # White alone
            'B02001_003E',            # Black or African American alone
            'B02001_004E',            # American Indian and Alaska Native alone
            'B02001_005E',            # Asian alone
            'B02001_006E',            # Native Hawaiian and Other Pacific Islander alone
            'B03003_002E',            # Hispanic or Latino
            'B03003_003E',            # Not Hispanic or Latino
            'B05003_001E',            # Voting age population
            'B01002_001E'             # Median age
        ]
        
        url = f"{CENSUS_API_BASE_URL}?get={','.join(variables)}&for=state:{state_code}&key={CENSUS_API_KEY}"
        logger.debug(f"Fetching all data in one call from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(url, headers=headers, allow_redirects=True)
        
        # Log response details
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Response content: {response.text[:500]}")  # First 500 chars
        
        if response.status_code == 403:
            logger.error(f"API Key error. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {"error": "Invalid Census API key. Please check your configuration."}, 400
        
        if response.status_code != 200:
            logger.error(f"API request failed. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {"error": f"API request failed with status code {response.status_code}"}, 400

        try:
            data = response.json()
            if not isinstance(data, list) or len(data) < 2:
                logger.error(f"Invalid response format: {data}")
                return {"error": "Invalid response format from Census API"}, 400
            
            # Extract data from the single response
            row = data[1]  # First row contains headers, second row contains values
            
            # Calculate total for ethnicity percentages
            total_ethnicity = int(row[7]) + int(row[8])  # Hispanic + Non-Hispanic
            
            # Prepare the response
            return {
                "state_code": state_code,
                "state_name": row[0],
                "total_population": int(row[1]),
                "race_distribution": {
                    "White": int(row[2]),
                    "Black": int(row[3]),
                    "American Indian": int(row[4]),
                    "Asian": int(row[5]),
                    "Other": int(row[6])
                },
                "ethnicity_distribution": {
                    "Hispanic": round((int(row[7]) / total_ethnicity) * 100, 1),
                    "Non-Hispanic": round((int(row[8]) / total_ethnicity) * 100, 1)
                },
                "voting_age_population": int(row[9]),
                "median_age": float(row[10])
            }
            
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse response data: {e}")
            logger.error(f"Response content: {response.text}")
            return {"error": "Failed to parse Census API response"}, 400

    except Exception as e:
        logger.error(f"Error fetching data for state {state_code}: {str(e)}")
        return {"error": f"Failed to fetch data: {str(e)}"}, 500

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

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
    parser = argparse.ArgumentParser(description='Run the Census App')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the application on (default: 5001)')
    args = parser.parse_args()
    
    app.run(host='0.0.0.0', port=args.port, debug=True) 