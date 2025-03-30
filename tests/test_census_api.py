import unittest
from unittest.mock import patch, MagicMock
from api.census_api import CensusAPI, StateData

class TestCensusAPI(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api = CensusAPI(api_key="test_key")
        self.mock_response = [
            ["NAME", "B01003_001E", "B02001_002E", "B02001_003E", "B02001_004E", "B02001_005E", "B02001_006E", "B03003_002E", "B03003_003E", "B05003_001E", "B01002_001E", "state"],
            ["Colorado", "5773714", "4634305", "235692", "53671", "181733", "8883", "4521234", "1252480", "5773714", "36.9", "08"]
        ]

    def test_init(self):
        """Test CensusAPI initialization."""
        self.assertEqual(self.api.api_key, "test_key")
        self.assertEqual(self.api.base_url, "https://api.census.gov/data/2020/acs/acs5")

    @patch('requests.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response
        mock_get.return_value = mock_response

        data, error, status_code = self.api.make_request("test_endpoint")
        self.assertEqual(data, self.mock_response)
        self.assertIsNone(error)
        self.assertIsNone(status_code)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_make_request_invalid_key(self, mock_get):
        """Test API request with invalid key."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Invalid key"
        mock_get.return_value = mock_response

        data, error, status_code = self.api.make_request("test_endpoint")
        self.assertIsNone(data)
        self.assertEqual(error, {"error": "Invalid Census API key. Please check your configuration."})
        self.assertEqual(status_code, 400)

    @patch('requests.get')
    def test_make_request_rate_limit(self, mock_get):
        """Test API request with rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.json.return_value = {"message": "Rate limit exceeded"}
        mock_get.return_value = mock_response

        data, error, status_code = self.api.make_request("test_endpoint")
        self.assertIsNone(data)
        self.assertEqual(error, {"error": "API request failed: Rate limit exceeded"})
        self.assertEqual(status_code, 429)

    @patch('requests.get')
    def test_get_state_data_success(self, mock_get):
        """Test successful state data retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response
        mock_get.return_value = mock_response

        state_data, error, status_code = self.api.get_state_data("08")
        self.assertIsInstance(state_data, StateData)
        self.assertIsNone(error)
        self.assertIsNone(status_code)
        self.assertEqual(state_data.state_code, "08")
        self.assertEqual(state_data.state_name, "Colorado")
        self.assertEqual(state_data.total_population, 5773714)
        self.assertEqual(state_data.race_distribution["White"], 4634305)
        self.assertEqual(state_data.race_distribution["Black"], 235692)
        self.assertEqual(state_data.race_distribution["American Indian"], 53671)
        self.assertEqual(state_data.race_distribution["Asian"], 181733)
        self.assertEqual(state_data.race_distribution["Other"], 8883)
        self.assertEqual(state_data.ethnicity_distribution["Hispanic"], 78.3)
        self.assertEqual(state_data.ethnicity_distribution["Non-Hispanic"], 21.7)
        self.assertEqual(state_data.voting_age_population, 5773714)
        self.assertEqual(state_data.median_age, 36.9)

    @patch('requests.get')
    def test_get_state_data_invalid_response(self, mock_get):
        """Test state data retrieval with invalid response format."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [["invalid", "format"]]
        mock_get.return_value = mock_response

        data, error, status_code = self.api.get_state_data("08")
        self.assertIsNone(data)
        self.assertEqual(error, {"error": "Invalid response format from Census API"})
        self.assertEqual(status_code, 400)

    @patch('requests.get')
    def test_get_state_data_caching(self, mock_get):
        """Test that state data is cached after first request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response
        mock_get.return_value = mock_response

        # First request
        self.api.get_state_data("08")
        initial_call_count = mock_get.call_count

        # Second request for same state
        self.api.get_state_data("08")
        self.assertEqual(mock_get.call_count, initial_call_count)

        # Request for different state
        self.api.get_state_data("09")
        self.assertEqual(mock_get.call_count, initial_call_count + 1)

if __name__ == '__main__':
    unittest.main()
