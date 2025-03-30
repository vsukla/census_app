# US Census Data Visualization App

A Flask web application that visualizes US Census data using interactive charts and tables. The application fetches demographic data from the US Census Bureau API and presents it in an easy-to-understand format.

## Features

- Interactive state selection
- Race distribution visualization
- Ethnicity distribution visualization
- Population trends over time
- Key demographic statistics
- Rate-limited API endpoints
- Secure headers and content security policy

## Prerequisites

- Python 3.8 or higher
- US Census Bureau API key

## Installation

1. Clone the repository:
```bash
# Using HTTPS
git clone https://github.com/yourusername/census_app.git

# Or using SSH (recommended)
git clone git@github.com:yourusername/census_app.git

cd census_app
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your Census API key:
```
CENSUS_API_KEY=your_api_key_here
```

## Usage

1. Start the Flask development server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Select a state from the dropdown menu to view its demographic data.

## API Endpoints

- `GET /`: Home page with state selection
- `GET /api/state/<state_code>`: Get demographic data for a specific state

## Security Features

- Content Security Policy (CSP)
- Rate limiting
- Secure headers
- HTTPS enforcement (in production)

## Development

The application uses:
- Flask for the web framework
- Chart.js for data visualization
- Flask-Talisman for security headers
- Flask-Limiter for rate limiting

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 