import json
import logging
import requests
from functools import lru_cache
from typing import Dict, Optional, Tuple, Any
from .state_data import StateData

logger = logging.getLogger(__name__)

class CensusAPI:
    """Class to handle Census API interactions"""
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def make_request(self, url: str) -> Tuple[Optional[list], Optional[Dict[str, str]], Optional[int]]:
        """Make a request to the Census API with proper headers and error handling"""
        logger.debug(f"Making request to URL: {url}")
        response = requests.get(url, headers=self.headers, allow_redirects=True)
        
        # Log response details
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Response content: {response.text[:500]}")  # First 500 chars
        
        if response.status_code == 403:
            logger.error(f"API Key error. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None, {"error": "Invalid Census API key. Please check your configuration."}, 400
        
        if response.status_code != 200:
            logger.error(f"API request failed. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            try:
                error_data = response.json()
                error_message = error_data.get('message', 'Unknown error')
            except:
                error_message = response.text
            return None, {"error": f"API request failed: {error_message}"}, response.status_code

        try:
            data = response.json()
            if not isinstance(data, list) or len(data) < 2:
                logger.error(f"Invalid response format: {data}")
                return None, {"error": "Invalid response format from Census API"}, 400
            return data, None, None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response.text}")
            return None, {"error": "Failed to parse Census API response"}, 400

    @lru_cache(maxsize=50)
    def get_state_data(self, state_code: str) -> Tuple[Optional[StateData], Optional[Dict[str, str]], Optional[int]]:
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
            
            url = f"{self.base_url}?get={','.join(variables)}&for=state:{state_code}&key={self.api_key}"
            logger.debug(f"Fetching all data in one call from: {url}")
            
            data, error, status_code = self.make_request(url)
            if error:
                return None, error, status_code
            
            # Extract data from the single response
            row = data[1]  # First row contains headers, second row contains values
            
            # Calculate total for ethnicity percentages
            total_ethnicity = int(row[7]) + int(row[8])  # Hispanic + Non-Hispanic
            
            # Create StateData object
            state_data = StateData(
                state_code=state_code,
                state_name=row[0],
                total_population=int(row[1]),
                race_distribution={
                    "White": int(row[2]),
                    "Black": int(row[3]),
                    "American Indian": int(row[4]),
                    "Asian": int(row[5]),
                    "Other": int(row[6])
                },
                ethnicity_distribution={
                    "Hispanic": round((int(row[7]) / total_ethnicity) * 100, 1),
                    "Non-Hispanic": round((int(row[8]) / total_ethnicity) * 100, 1)
                },
                voting_age_population=int(row[9]),
                median_age=float(row[10])
            )
            
            return state_data, None, None
            
        except Exception as e:
            logger.error(f"Error fetching data for state {state_code}: {str(e)}")
            return None, {"error": f"Failed to fetch data: {str(e)}"}, 500 