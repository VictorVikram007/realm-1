import requests
import time
from functools import lru_cache

WEATHER_API_KEY = '77ebd6df4093472295e184847260603'
BASE_URL = 'https://api.weatherapi.com/v1'

# We use lru_cache for simple in-memory caching to avoid rate limits
# maxsize=128 caches up to 128 distinct city requests
@lru_cache(maxsize=128)
def _fetch_current_weather_cached(city, cache_buster):
    url = f"{BASE_URL}/current.json?key={WEATHER_API_KEY}&q={city}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

@lru_cache(maxsize=128)
def _fetch_forecast_weather_cached(city, days, cache_buster):
    url = f"{BASE_URL}/forecast.json?key={WEATHER_API_KEY}&q={city}&days={days}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def fetch_current_weather(city):
    """Fetch current weather with a 15-minute cache window."""
    # cache_buster changes every 15 minutes (900 seconds)
    cache_buster = int(time.time() / 900)
    try:
        return _fetch_current_weather_cached(city, cache_buster)
    except Exception as e:
        print(f"[ERROR] WeatherAPI current fetch failed for {city}: {e}")
        return None

def fetch_forecast_weather(city, days=3):
    """Fetch forecast weather with a 30-minute cache window."""
    # cache_buster changes every 30 minutes (1800 seconds)
    cache_buster = int(time.time() / 1800)
    try:
        return _fetch_forecast_weather_cached(city, days, cache_buster)
    except Exception as e:
        print(f"[ERROR] WeatherAPI forecast fetch failed for {city}: {e}")
        return None
