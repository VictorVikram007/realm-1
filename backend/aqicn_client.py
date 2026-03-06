"""
AQICN API Client
Fetches real-time AQI data from the World Air Quality Index API.
Includes caching and graceful fallback.
"""

import requests
import time
import json
import os

# Demo token — works for development. Replace with your own from:
# https://aqicn.org/data-platform/token/
AQICN_TOKEN = os.environ.get('AQICN_TOKEN', '6ca1942d1ee54d5861b2f505221e07512bd8b646')
AQICN_BASE_URL = 'https://api.waqi.info'

# Simple in-memory cache with 5-minute TTL
_cache = {}
CACHE_TTL = 300  # seconds


def _get_cached(key):
    """Return cached value if still valid, else None."""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key, data):
    """Store data in cache."""
    _cache[key] = (data, time.time())


def fetch_city_aqi(city):
    """
    Fetch real-time AQI for a city.

    Args:
        city: City name (e.g., 'delhi', 'mumbai')

    Returns:
        Dict with AQI data or None on failure
    """
    cache_key = f'city_{city.lower()}'
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        url = f'{AQICN_BASE_URL}/feed/{city}/?token={AQICN_TOKEN}'
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok':
            print(f"[WARN] AQICN returned non-ok status for {city}: {data.get('data')}")
            return None

        result = _parse_feed_response(data['data'])
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[ERROR] AQICN API error for {city}: {e}")
        return None


def search_stations(keyword):
    """
    Search AQICN stations by keyword.

    Args:
        keyword: Search term (city, station name, etc.)

    Returns:
        List of matching stations or empty list on failure
    """
    cache_key = f'search_{keyword.lower()}'
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        url = f'{AQICN_BASE_URL}/search/?keyword={keyword}&token={AQICN_TOKEN}'
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok':
            return []

        results = []
        for item in data.get('data', []):
            results.append({
                'uid': item.get('uid'),
                'name': item.get('station', {}).get('name', ''),
                'aqi': item.get('aqi', 'N/A'),
                'time': item.get('time', {}).get('stime', ''),
                'geo': item.get('station', {}).get('geo', []),
            })

        _set_cache(cache_key, results)
        return results
    except Exception as e:
        print(f"[ERROR] AQICN search error for {keyword}: {e}")
        return []


def fetch_station_by_id(station_id):
    """
    Fetch AQI data for a specific station by its UID.

    Args:
        station_id: AQICN station UID

    Returns:
        Dict with AQI data or None
    """
    cache_key = f'station_{station_id}'
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        url = f'{AQICN_BASE_URL}/feed/@{station_id}/?token={AQICN_TOKEN}'
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('status') != 'ok':
            return None

        result = _parse_feed_response(data['data'])
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[ERROR] AQICN station fetch error for {station_id}: {e}")
        return None


def fetch_india_map_data():
    """
    Fetch AQI data for major Indian cities from AQICN.

    Returns:
        List of city AQI data points
    """
    cache_key = 'india_map'
    cached = _get_cached(cache_key)
    if cached:
        return cached

    major_cities = [
        'delhi', 'mumbai', 'bangalore', 'kolkata', 'chennai',
        'hyderabad', 'ahmedabad', 'pune', 'lucknow', 'jaipur',
        'patna', 'chandigarh', 'gurgaon', 'noida', 'varanasi',
        'agra', 'kanpur', 'nagpur', 'indore', 'bhopal',
    ]

    results = []
    for city in major_cities:
        data = fetch_city_aqi(city)
        if data:
            results.append(data)

    if results:
        _set_cache(cache_key, results)
    return results


def _parse_feed_response(data):
    """Parse AQICN feed response into clean dict."""
    iaqi = data.get('iaqi', {})

    result = {
        'aqi': data.get('aqi'),
        'station': data.get('city', {}).get('name', ''),
        'geo': data.get('city', {}).get('geo', []),
        'time': data.get('time', {}).get('s', ''),
        'dominant_pollutant': data.get('dominentpol', ''),
        'pollutants': {},
        'weather': {},
    }

    # Extract individual pollutant values
    pollutant_keys = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
    for key in pollutant_keys:
        if key in iaqi:
            result['pollutants'][key] = iaqi[key].get('v')

    # Extract weather data if available
    weather_keys = ['t', 'h', 'p', 'w', 'wg']
    weather_labels = {'t': 'temperature', 'h': 'humidity', 'p': 'pressure', 'w': 'wind', 'wg': 'wind_gust'}
    for key in weather_keys:
        if key in iaqi:
            result['weather'][weather_labels[key]] = iaqi[key].get('v')

    return result


def get_status():
    """Check if AQICN API is accessible."""
    try:
        resp = requests.get(f'{AQICN_BASE_URL}/feed/delhi/?token={AQICN_TOKEN}', timeout=5)
        return resp.status_code == 200 and resp.json().get('status') == 'ok'
    except:
        return False


if __name__ == '__main__':
    print("Testing AQICN API client...")
    print(f"API Status: {'✓ Online' if get_status() else '✗ Offline'}")

    print("\nFetching Delhi AQI...")
    delhi = fetch_city_aqi('delhi')
    if delhi:
        print(json.dumps(delhi, indent=2))
    else:
        print("  Could not fetch data (demo token may be rate-limited)")

    print("\nSearching for 'mumbai'...")
    results = search_stations('mumbai')
    for r in results[:3]:
        print(f"  {r['name']} — AQI: {r['aqi']}")
