import os
import json
import boto3
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

class WeatherDashboard:
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')
        self.s3_client = boto3.client('s3')

    def create_bucket_if_not_exists(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket {self.bucket_name} exists")
        except:
            print(f"Creating bucket {self.bucket_name}")
        try:
            self.s3_client.create_bucket(Bucket=self.bucket_name)
            print(f"Successfully created bucket {self.bucket_name}")
        except Exception as e:
            print(f"Error creating bucket: {e}")

    def fetch_weather(self, city):
        """Fetch weather data from OpenWeather API"""
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "imperial"
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    def save_to_s3(self, weather_data, city):
        """Save weather data to S3 bucket"""
        if not weather_data:
            return False
            
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        file_name = f"weather-data/{city}-{timestamp}.json"
        
        try:
            weather_data['timestamp'] = timestamp
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=json.dumps(weather_data),
                ContentType='application/json'
            )
            print(f"Successfully saved data for {city} to S3")
            return True
        except Exception as e:
            print(f"Error saving to S3: {e}")
            return False

def fetch_weather_for_dashboard(cities):
    """Fetch weather data for multiple cities and return as a DataFrame"""
    dashboard = WeatherDashboard()
    weather_data = []

    for city in cities:
        city = city.strip()
        data = dashboard.fetch_weather(city)
        if data:
            weather_data.append({
                "City": city,
                "Temperature (°F)": data['main']['temp'],
                "Feels Like (°F)": data['main']['feels_like'],
                "Humidity (%)": data['main']['humidity'],
                "Conditions": data['weather'][0]['description'],
                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    return pd.DataFrame(weather_data)

# Streamlit Dashboard
def streamlit_dashboard():
    st.title("Weather Dashboard 🌦️")
    st.sidebar.header("Settings")

    # Get user input
    cities = st.sidebar.text_input("Enter cities (comma-separated)", "Philadelphia, Seattle, New York").split(",")

    if st.sidebar.button("Fetch Weather"):
        # Fetch weather data
        df = fetch_weather_for_dashboard(cities)
        if not df.empty:
            st.header("Weather Data")
            st.dataframe(df)

            # Visualizations
            st.subheader("Temperature Comparison")
            st.bar_chart(df.set_index("City")[["Temperature (°F)", "Feels Like (°F)"]])

            st.subheader("Humidity Comparison")
            st.bar_chart(df.set_index("City")["Humidity (%)"])

            st.subheader("Conditions Overview")
            st.table(df[["City", "Conditions"]])

        else:
            st.error("Failed to fetch weather data for the cities provided.")

# Run the Streamlit dashboard
if __name__ == "__main__":
    streamlit_dashboard()
