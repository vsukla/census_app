# Flask and extensions
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Standard library
import logging
import os
import re
import argparse
from dotenv import load_dotenv

# Third-party
from api.census_api import CensusAPI

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

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Census API configuration
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY')
CENSUS_API_BASE_URL = 'https://api.census.gov/data/2020/acs/acs5'

if not CENSUS_API_KEY:
    logger.error("CENSUS_API_KEY environment variable is not set")
    raise ValueError("CENSUS_API_KEY environment variable is required")

logger.info(f"Using Census API Key: {CENSUS_API_KEY[:5]}...")

# Initialize Census API
census_api = CensusAPI(CENSUS_API_KEY, CENSUS_API_BASE_URL)

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

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/state/<state_code>', methods=['GET'])
@limiter.limit("30 per minute")
def get_state_api(state_code):
    """API endpoint to get state demographic data"""
    if not re.match(r'^[0-9]{2}$', state_code):
        return jsonify({"error": "Invalid state code format"}), 400
    
    state_data, error, status_code = census_api.get_state_data(state_code)
    if error:
        return jsonify(error), status_code
    
    return jsonify(state_data.to_dict())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Census App')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the application on (default: 5001)')
    args = parser.parse_args()
    
    app.run(host='0.0.0.0', port=args.port, debug=True) 