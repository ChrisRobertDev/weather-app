from flask import Flask, render_template, request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, time

#functions
def get_weather_data(data):
    filtered_data = []
    for forecast in data['forecast']['forecastday'][:3]:
        day_data = {
            'date': forecast['date'],
            'city': data['location']['name'],
            'max_temperature': forecast['day']['maxtemp_c'],
            'min_temperature': forecast['day']['mintemp_c'],
            'total_precipitation': forecast['day']['totalprecip_mm'],
            'sunrise_hour': forecast['astro']['sunrise'],
            'sunset_hour': forecast['astro']['sunset']
        }
        filtered_data.append(day_data)
    return filtered_data
    

def addToDB(filtered_data):
    try:
        for day_data in filtered_data:
            existing_forecast = WeatherForecast.query.filter_by(date=datetime.strptime(day_data['date'], '%Y-%m-%d').date(), city=day_data['city']).first()
            if existing_forecast:
                existing_forecast.max_temperature = day_data['max_temperature']
                existing_forecast.min_temperature = day_data['min_temperature']
                existing_forecast.total_precipitation = day_data['total_precipitation']
                existing_forecast.sunrise_hour = datetime.strptime(day_data['sunrise_hour'], '%I:%M %p').time()
                existing_forecast.sunset_hour = datetime.strptime(day_data['sunset_hour'], '%I:%M %p').time()
            else:
                weather_forecast = WeatherForecast(
                    date=datetime.strptime(day_data['date'], '%Y-%m-%d').date(),
                    city=day_data['city'],
                    max_temperature=day_data['max_temperature'],
                    min_temperature=day_data['min_temperature'],
                    total_precipitation=day_data['total_precipitation'],
                    sunrise_hour=datetime.strptime(day_data['sunrise_hour'], '%I:%M %p').time(),
                    sunset_hour=datetime.strptime(day_data['sunset_hour'], '%I:%M %p').time()
                )
                db.session.merge(weather_forecast)

        db.session.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
        db.session.rollback()

#global variables

# Initialize Flask app
app = Flask(__name__)

# Load environment variables from .env into os.environ
load_dotenv()

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
db = SQLAlchemy(app)

# Initialize Bootstrap
bootstrap = Bootstrap(app)

# model Class definition
class WeatherForecast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    max_temperature = db.Column(db.Float, nullable=False)
    min_temperature = db.Column(db.Float, nullable=False)
    total_precipitation = db.Column(db.Float, nullable=False)
    sunrise_hour = db.Column(db.Time, nullable=False)
    sunset_hour = db.Column(db.Time, nullable=False)
    
with app.app_context():
    db.create_all()

# Define routes and views
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/process_form', methods=['POST'])
def process_form():
    city = request.form['city']
    api_key = os.environ.get('WEATHER_API_KEY')
    url = f'http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=3'
    response = requests.get(url)
    data = response.json()
    filtered_data = get_weather_data(data)
    addToDB(filtered_data)
    forecasts = db.session.query(WeatherForecast).filter_by(city=city).all()
    return render_template('index.html', forecasts=forecasts)

#error handlers for rendering
@app.errorhandler(404)
def not_found_page(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error_page(error):
    return render_template('500.html'), 500
# Error handling for API requests
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Internal server error'}), 500
# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
