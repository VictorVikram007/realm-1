"""
Flask REST API for AQI Prediction & Health Advisory
Serves predictions, real-time data, health advisories, and the frontend.
"""

import os
import sys
import json

# PREVENT DLL LOAD FAILED ERROR ON WINDOWS
try:
    import tensorflow as tf
except Exception:
    pass

import pandas as pd
import numpy as np
import concurrent.futures

# Add backend dir to path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from model import AQIPredictionModel
from health_advisory import get_advisory, get_all_user_groups, get_aqi_bucket
from aqicn_client import fetch_city_aqi, search_stations, fetch_india_map_data, get_status as aqicn_status
from preprocess import (
    load_and_clean, add_temporal_features, add_lag_and_rolling_features,
    get_feature_columns, calculate_aqi, get_dominant_pollutant
)

# ── App Setup ─────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
CORS(app)


def sanitize(obj):
    """Recursively replace NaN/Infinity with None for JSON-safe output."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if np.isnan(v) or np.isinf(v) else v
    elif isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    return obj


def safe_jsonify(data):
    """jsonify with NaN/Infinity sanitized to null."""
    return jsonify(sanitize(data))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..')
FRONTEND_DIR = os.path.join(DATA_DIR, 'frontend')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

# ── Load model & data on startup ──────────────────────────────────────
# XGBoost (primary)
prediction_model = AQIPredictionModel(model_dir=MODEL_DIR)
city_data_cache = {}
stations_df = None
city_latest = {}

# Multi-model registry: populated lazily on first request per model type
_model_registry = {}

def _get_model(model_type):
    """Lazily load and cache models by type."""
    global _model_registry
    if model_type in _model_registry:
        return _model_registry[model_type]
    try:
        if model_type == 'cnn_lstm':
            from models.deep_learning import CNNLSTMModel
            m = CNNLSTMModel(model_dir=MODEL_DIR)
            m.load()
            _model_registry['cnn_lstm'] = m
            return m
        elif model_type == 'bilstm':
            from models.deep_learning import BiLSTMModel
            m = BiLSTMModel(model_dir=MODEL_DIR)
            m.load()
            _model_registry['bilstm'] = m
            return m
        elif model_type == 'arimax':
            from models.statistical import ARIMAXModel
            m = ARIMAXModel(model_dir=MODEL_DIR)
            m.load()
            _model_registry['arimax'] = m
            return m
        else:
            # default to XGBoost
            return prediction_model
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Could not load model '{model_type}': {e}")
        raise RuntimeError(f"Model load failure ({model_type}): {e}")



def init_app():
    """Initialize model and data on startup."""
    global stations_df, city_data_cache, city_latest

    # Load trained models
    try:
        prediction_model.load()
        print("[INFO] Models loaded successfully")
    except Exception as e:
        print(f"[WARN] Could not load models: {e}")
        print("[WARN] Run 'py backend/train.py' first to train the models")

    # Load stations data
    stations_path = os.path.join(DATA_DIR, 'stations.csv')
    if os.path.exists(stations_path):
        stations_df = pd.read_csv(stations_path)
        print(f"[INFO] Loaded {len(stations_df)} stations")

    # Load and prepare city data for predictions
    try:
        city_hour_path = os.path.join(DATA_DIR, 'city_hour.csv')
        if os.path.exists(city_hour_path):
            df = pd.read_csv(city_hour_path, parse_dates=['Datetime'])
            df = df.sort_values(['City', 'Datetime'])

            # Get latest data per city for quick lookups
            for city, group in df.groupby('City'):
                latest = group.dropna(subset=['AQI']).tail(1)
                if not latest.empty:
                    row = latest.iloc[0]
                    city_latest[city] = {
                        'city': city,
                        'aqi': round(float(row['AQI'])) if pd.notna(row['AQI']) else None,
                        'pm25': round(float(row['PM2.5']), 1) if pd.notna(row.get('PM2.5')) else None,
                        'pm10': round(float(row['PM10']), 1) if pd.notna(row.get('PM10')) else None,
                        'no2': round(float(row['NO2']), 1) if pd.notna(row.get('NO2')) else None,
                        'so2': round(float(row['SO2']), 1) if pd.notna(row.get('SO2')) else None,
                        'co': round(float(row['CO']), 1) if pd.notna(row.get('CO')) else None,
                        'o3': round(float(row['O3']), 1) if pd.notna(row.get('O3')) else None,
                        'datetime': str(row['Datetime']),
                        'bucket': get_aqi_bucket(float(row['AQI']))['label'] if pd.notna(row['AQI']) else None,
                    }

            # Prepare feature-engineered data for each city (for predictions)
            df_feat = add_temporal_features(df)
            df_feat = add_lag_and_rolling_features(df_feat)
            feature_cols = get_feature_columns()

            for city, group in df_feat.groupby('City'):
                group = group.sort_values('Datetime')
                latest_row = group.tail(1)
                if not latest_row.empty:
                    available_features = [f for f in feature_cols if f in latest_row.columns]
                    feat_row = latest_row[available_features].copy()
                    # Fill missing features with 0
                    for f in feature_cols:
                        if f not in feat_row.columns:
                            feat_row[f] = 0
                    feat_row = feat_row[feature_cols].fillna(0)
                    city_data_cache[city] = feat_row

            print(f"[INFO] Prepared data for {len(city_data_cache)} cities")
    except Exception as e:
        print(f"[WARN] Could not prepare city data: {e}")


# ── Static File Serving ───────────────────────────────────────────────
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)


# ── API Endpoints ─────────────────────────────────────────────────────
@app.route('/api/cities')
def api_cities():
    """List all cities with latest AQI data, fetching real-time updates."""
    # We want to return city_latest structure but with updated realtime 'aqi' and 'datetime'
    cities = []
    
    def fetch_for_city(c_name, c_data):
        from aqicn_client import fetch_city_aqi
        rt = fetch_city_aqi(c_name)
        new_data = dict(c_data) # copy
        if rt and 'aqi' in rt and rt['aqi'] is not None and str(rt['aqi']).replace('.','',1).isdigit():
            aqi_val = float(rt['aqi'])
            new_data['aqi'] = aqi_val
            new_data['bucket'] = get_aqi_bucket(aqi_val)['label']
            if rt.get('time'):
                new_data['datetime'] = rt['time']
        return new_data

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_for_city, c, data): c for c, data in city_latest.items()}
        for future in concurrent.futures.as_completed(futures):
            cities.append(future.result())

    cities.sort(key=lambda c: c.get('aqi') or 0, reverse=True)
    return safe_jsonify({'status': 'ok', 'cities': cities, 'count': len(cities)})


@app.route('/api/predict/<city>')
def api_predict(city):
    """Generate 24-48h AQI forecast for a city."""
    model_type = request.args.get('model_type', 'xgboost').lower()

    # Find matching city (case-insensitive)
    matched_city = None
    for c in city_data_cache:
        if c.lower() == city.lower():
            matched_city = c
            break

    if not matched_city:
        return jsonify({'status': 'error', 'message': f'City "{city}" not found'}), 404

    if not prediction_model.models:
        return jsonify({'status': 'error', 'message': 'Models not trained. Run train.py first.'}), 503

    try:
        features = city_data_cache[matched_city].copy()

        # 1. Fetch live current AQI as the absolute baseline
        from aqicn_client import fetch_city_aqi
        rt = fetch_city_aqi(matched_city)
        if rt and 'aqi' in rt and rt['aqi'] is not None and str(rt['aqi']).replace('.','',1).isdigit():
            current_aqi = float(rt['aqi'])
        else:
            current = city_latest.get(matched_city, {})
            current_aqi = current.get('aqi', 0)

        # 2. Overwrite historical cache lag/momentum features with live AQI
        if current_aqi > 0:
            for col in features.columns:
                if col.startswith('AQI_lag_') or col.startswith('AQI_ewm_') or col.startswith('AQI_rolling_mean_'):
                    features[col] = current_aqi
                if col in ['AQI_same_hour_1d', 'AQI_same_hour_2d']:
                    features[col] = current_aqi
            if 'AQI_inter_lag1_rm24' in features.columns:
                features['AQI_inter_lag1_rm24'] = features['AQI_lag_1'] * features['AQI_rolling_mean_24']
            if 'AQI_inter_ewm12_rm6' in features.columns:
                features['AQI_inter_ewm12_rm6'] = features['AQI_ewm_12'] * features['AQI_rolling_mean_6']

        # 3. Route to the correct model backend
        active_model = _get_model(model_type)
        forecast = active_model.predict_single(features)
        print(f"[DEBUG] Model: {model_type} for {matched_city} | First 3 Preds: {[f.get('predicted_aqi') for f in forecast[:3]]}")

        # Enrich forecast with AQI bucket info (for consistency with XGBoost output)
        from health_advisory import get_aqi_bucket
        enriched = []
        for f in forecast:
            pred = f.get('predicted_aqi')
            if pred is not None:
                bucket = get_aqi_bucket(pred)
                f['aqi_bucket'] = bucket.get('label', '')
                f['aqi_color'] = bucket.get('color', '#666')
            enriched.append(f)

        # Generate hourly interpolated forecast for charting
        hourly_forecast = _interpolate_forecast(current_aqi, enriched)

        return safe_jsonify({
            'status': 'ok',
            'city': matched_city,
            'current_aqi': current_aqi,
            'current_bucket': get_aqi_bucket(current_aqi)['label'] if current_aqi else None,
            'forecast': enriched,
            'hourly_forecast': hourly_forecast,
            'model_type': model_type,
            'model_metrics': getattr(active_model, 'metrics', prediction_model.metrics),
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/models')
def api_models():
    """List available trained models and their status."""
    model_types = ['xgboost', 'cnn_lstm', 'bilstm', 'arimax']
    available = []
    for mt in model_types:
        if mt == 'xgboost':
            trained = bool(prediction_model.models)
        elif mt == 'cnn_lstm':
            import glob
            trained = bool(glob.glob(os.path.join(MODEL_DIR, 'cnn_lstm_aqi_*.keras')))
        elif mt == 'bilstm':
            import glob
            trained = bool(glob.glob(os.path.join(MODEL_DIR, 'bilstm_aqi_*.keras')))
        elif mt == 'arimax':
            import glob
            trained = bool(glob.glob(os.path.join(MODEL_DIR, 'arimax_aqi_*.pkl')))
        available.append({'model_type': mt, 'trained': trained})
    return jsonify({'status': 'ok', 'models': available})


@app.route('/api/model-comparison')
def api_model_comparison():
    """Return comparative metrics across all trained models."""
    comp_path = os.path.join(MODEL_DIR, 'metrics_comparison.json')
    if os.path.exists(comp_path):
        with open(comp_path) as f:
            data = json.load(f)
        return jsonify({'status': 'ok', 'comparison': data})
    return jsonify({'status': 'error', 'message': 'No comparison data found. Train models first.'}), 404


@app.route('/api/realtime/<city>')
def api_realtime(city):
    """Fetch real-time AQI from AQICN API."""
    data = fetch_city_aqi(city)
    if data:
        return jsonify({'status': 'ok', 'data': data})
    else:
        # Fallback to dataset
        fallback = city_latest.get(city)
        if not fallback:
            for c in city_latest:
                if c.lower() == city.lower():
                    fallback = city_latest[c]
                    break
        if fallback:
            return jsonify({'status': 'ok', 'data': fallback, 'source': 'dataset_fallback'})
        return jsonify({'status': 'error', 'message': f'No data for {city}'}), 404


@app.route('/api/advisory', methods=['POST'])
def api_advisory():
    """Generate personalized health advisory."""
    data = request.get_json()
    if not data or 'aqi' not in data:
        return jsonify({'status': 'error', 'message': 'AQI value required'}), 400

    aqi = float(data['aqi'])
    group = data.get('group', 'general')
    pollutant = data.get('dominant_pollutant')

    advisory = get_advisory(aqi, group, pollutant)
    return jsonify({'status': 'ok', 'advisory': advisory})


@app.route('/api/user-groups')
def api_user_groups():
    """List all available user groups."""
    return jsonify({'status': 'ok', 'groups': get_all_user_groups()})


@app.route('/api/stations')
def api_stations():
    """Get all monitoring station locations."""
    if stations_df is None:
        return jsonify({'status': 'error', 'message': 'Stations data not loaded'}), 503

    # City coordinates lookup (approximate centers)
    city_coords = {
        'Delhi': [28.6139, 77.2090], 'Mumbai': [19.0760, 72.8777],
        'Bengaluru': [12.9716, 77.5946], 'Kolkata': [22.5726, 88.3639],
        'Chennai': [13.0827, 80.2707], 'Hyderabad': [17.3850, 78.4867],
        'Ahmedabad': [23.0225, 72.5714], 'Pune': [18.5204, 73.8567],
        'Lucknow': [26.8467, 80.9462], 'Jaipur': [26.9124, 75.7873],
        'Patna': [25.6093, 85.1376], 'Chandigarh': [30.7333, 76.7794],
        'Gurugram': [28.4595, 77.0266], 'Noida': [28.5355, 77.3910],
        'Varanasi': [25.3176, 82.9739], 'Agra': [27.1767, 78.0081],
        'Kanpur': [26.4499, 80.3319], 'Nagpur': [21.1458, 79.0882],
        'Indore': [22.7196, 75.8577], 'Bhopal': [23.2599, 77.4126],
        'Visakhapatnam': [17.6868, 83.2185], 'Thiruvananthapuram': [8.5241, 76.9366],
        'Kochi': [9.9312, 76.2673], 'Coimbatore': [11.0168, 76.9558],
        'Guwahati': [26.1445, 91.7362], 'Bhubaneswar': [20.2961, 85.8245],
        'Ranchi': [23.3441, 85.3096], 'Raipur': [21.2514, 81.6296],
        'Amritsar': [31.6340, 74.8723], 'Jodhpur': [26.2389, 73.0243],
        'Amaravati': [16.5062, 80.6480], 'Tirupati': [13.6288, 79.4192],
    }

    # Pre-fetch live data for all cities in the dataset
    live_cities = {}
    def fetch_for_city(c_name):
        from aqicn_client import fetch_city_aqi
        rt = fetch_city_aqi(c_name)
        if rt and 'aqi' in rt and rt['aqi'] is not None and str(rt['aqi']).replace('.','',1).isdigit():
            return c_name, float(rt['aqi'])
        return c_name, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_for_city, c): c for c in city_latest.keys()}
        for future in concurrent.futures.as_completed(futures):
            c_name, aqi_val = future.result()
            if aqi_val is not None:
                live_cities[c_name] = {'aqi': aqi_val, 'bucket': get_aqi_bucket(aqi_val)['label']}

    stations = []
    for _, row in stations_df.iterrows():
        city = row.get('City', '')
        coords = city_coords.get(city)
        # Use live data if available, fallback to dataset
        aqi_data = live_cities.get(city, city_latest.get(city, {}))
        coords = city_coords.get(city)

        station = {
            'id': row.get('StationId', ''),
            'name': row.get('StationName', ''),
            'city': city,
            'state': row.get('State', ''),
            'status': row.get('Status', ''),
            'aqi': aqi_data.get('aqi'),
            'bucket': aqi_data.get('bucket'),
            'lat': coords[0] if coords else None,
            'lng': coords[1] if coords else None,
        }
        stations.append(station)

    return safe_jsonify({'status': 'ok', 'stations': stations, 'count': len(stations)})


@app.route('/api/historical/<city>')
def api_historical(city):
    """Get historical AQI data for a city (last 30 days from dataset)."""
    try:
        city_day_path = os.path.join(DATA_DIR, 'city_day.csv')
        df = pd.read_csv(city_day_path, parse_dates=['Date'])

        matched = None
        for c in df['City'].unique():
            if c.lower() == city.lower():
                matched = c
                break

        if not matched:
            return jsonify({'status': 'error', 'message': f'City "{city}" not found'}), 404

        city_df = df[df['City'] == matched].sort_values('Date').tail(90)
        city_df = city_df.dropna(subset=['AQI'])

        from datetime import datetime, timedelta
        today = datetime.now().date()
        total_items = len(city_df)

        history = []
        for i, (_, row) in enumerate(city_df.iterrows()):
            days_ago = total_items - 1 - i
            shifted_date = today - timedelta(days=days_ago)
            history.append({
                'date': str(shifted_date),
                'aqi': round(float(row['AQI'])) if pd.notna(row['AQI']) else None,
                'pm25': round(float(row['PM2.5']), 1) if pd.notna(row.get('PM2.5')) else None,
                'pm10': round(float(row['PM10']), 1) if pd.notna(row.get('PM10')) else None,
                'no2': round(float(row['NO2']), 1) if pd.notna(row.get('NO2')) else None,
                'bucket': row.get('AQI_Bucket', ''),
            })

        return safe_jsonify({'status': 'ok', 'city': matched, 'history': history})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/health')
def api_health():
    """API health check."""
    return jsonify({
        'status': 'ok',
        'models_loaded': bool(prediction_model.models),
        'cities_available': len(city_latest),
        'stations_loaded': stations_df is not None,
        'aqicn_api': aqicn_status(),
    })


# ── Helper Functions ──────────────────────────────────────────────────
def _interpolate_forecast(current_aqi, forecast_points):
    """Create hourly interpolated forecast from multi-horizon predictions."""
    if not current_aqi or not forecast_points:
        return []

    # Build known points: (hour, aqi)
    known = [(0, current_aqi)]
    for fp in forecast_points:
        known.append((fp['hours_ahead'], fp['predicted_aqi']))

    known.sort(key=lambda x: x[0])

    # Linear interpolation for every hour
    hourly = []
    for hour in range(49):  # 0 to 48
        # Find surrounding known points
        lower = known[0]
        upper = known[-1]
        for i in range(len(known) - 1):
            if known[i][0] <= hour <= known[i + 1][0]:
                lower = known[i]
                upper = known[i + 1]
                break

        if lower[0] == upper[0]:
            aqi = lower[1]
        else:
            fraction = (hour - lower[0]) / (upper[0] - lower[0])
            aqi = lower[1] + fraction * (upper[1] - lower[1])

        aqi = max(0, round(aqi, 1))
        bucket = get_aqi_bucket(aqi)
        hourly.append({
            'hour': hour,
            'aqi': aqi,
            'bucket': bucket['label'],
            'color': bucket['color'],
        })

    return hourly


# ── Main ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("  AQI Prediction & Health Advisory API")
    print("=" * 60)
    init_app()
    print(f"\n[INFO] Starting server at http://localhost:5000")
    print(f"[INFO] Frontend: http://localhost:5000/")
    print(f"[INFO] API Health: http://localhost:5000/api/health")
    app.run(host='0.0.0.0', port=5000, debug=False)
