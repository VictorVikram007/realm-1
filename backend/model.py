"""
AQI Prediction Model — Multi-Horizon XGBoost Forecasting
Trains separate XGBoost models for 1h, 6h, 12h, 24h, and 48h ahead predictions.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error, mean_squared_error
import joblib
import os
import json


class AQIPredictionModel:
    """Multi-horizon AQI prediction using XGBoost ensemble."""

    HORIZONS = [1, 6, 12, 24, 48]  # hours ahead

    def __init__(self, model_dir=None):
        self.models = {}
        self.model_dir = model_dir or os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        self.metrics = {}

    def train(self, X_train, y_train_dict, X_val=None, y_val_dict=None):
        """
        Train XGBoost models for each horizon.

        Args:
            X_train: Training features DataFrame
            y_train_dict: Dict of {horizon: target_series}
            X_val: Validation features (optional)
            y_val_dict: Validation targets (optional)
        """
        for horizon in self.HORIZONS:
            target_col = f'AQI_target_{horizon}h'
            print(f"\n{'='*60}")
            print(f"Training model for {horizon}h ahead forecast...")
            print(f"{'='*60}")

            y_train = y_train_dict[target_col]

            # XGBoost parameters — Highly regularized to stop massive long-horizon overfitting
            if horizon <= 6:
                n_est, depth, lr = 1500, 6, 0.03
            elif horizon <= 12:
                n_est, depth, lr = 2000, 5, 0.02
            else:
                n_est, depth, lr = 3000, 5, 0.01

            params = {
                'n_estimators': n_est,
                'max_depth': depth,
                'learning_rate': lr,
                'subsample': 0.8,
                'colsample_bytree': 0.7,
                'min_child_weight': 10,
                'reg_alpha': 1.0,
                'reg_lambda': 5.0,
                'early_stopping_rounds': 50,
                'random_state': 42,
                'n_jobs': -1,
                'verbosity': 0,
            }

            model = xgb.XGBRegressor(**params)

            if X_val is not None and y_val_dict is not None:
                y_val = y_val_dict[target_col]
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=100
                )
            else:
                model.fit(X_train, y_train)

            self.models[horizon] = model

            # Training metrics — use filtered MAPE (exclude AQI < 20 which inflates %)
            train_pred = model.predict(X_train)
            train_mape = self._filtered_mape(y_train.values, train_pred)
            print(f"  Train MAPE ({horizon}h): {train_mape:.2f}%")

            if X_val is not None and y_val_dict is not None:
                val_pred = model.predict(X_val)
                val_mape = self._filtered_mape(y_val.values, val_pred)
                val_mae = mean_absolute_error(y_val, val_pred)
                val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
                print(f"  Val MAPE  ({horizon}h): {val_mape:.2f}%")
                print(f"  Val MAE   ({horizon}h): {val_mae:.2f}")
                print(f"  Val RMSE  ({horizon}h): {val_rmse:.2f}")

                self.metrics[horizon] = {
                    'mape': round(val_mape, 2),
                    'mae': round(val_mae, 2),
                    'rmse': round(val_rmse, 2),
                    'train_mape': round(train_mape, 2),
                }

    def predict(self, X):
        """
        Generate predictions for all horizons.

        Args:
            X: Feature DataFrame/array

        Returns:
            Dict of {horizon: predictions_array}
        """
        predictions = {}
        for horizon in self.HORIZONS:
            if horizon not in self.models:
                raise ValueError(f"No trained model for {horizon}h horizon. Train first.")
            predictions[horizon] = self.models[horizon].predict(X)
        return predictions

    def predict_single(self, X_row, future_weather=None):
        """
        Generate forecast for a single data point (latest observation).

        Args:
            X_row: Single row of features (DataFrame or 2D array)
            future_weather: List of hourly weather dicts mapping to future horizons.

        Returns:
            List of dicts with horizon, predicted AQI, and AQI bucket
        """
        forecast = []
        for horizon in self.HORIZONS:
            if horizon not in self.models:
                continue
                
            X_input = X_row.copy() if hasattr(X_row, 'copy') else X_row
            
            # If future weather is fetched, try projecting standard weather features into the future observation 
            if future_weather and isinstance(X_input, pd.DataFrame):
                # The AQI model was trained on historical data. If we had trained it on weather, we could apply it here.
                # Since the current models weren't inherently trained on weather variables (from preprocess.py review), 
                # we don't strictly *need* to inject feature columns here, but we pass them to establish the API pattern.
                if horizon < len(future_weather):
                    hw = future_weather[horizon]
                    # Only inject if the columns exist in the originally trained model features.
                    if 'temp_c' in X_input.columns: X_input['temp_c'] = hw.get('temp_c', 0)
                    if 'wind_kph' in X_input.columns: X_input['wind_kph'] = hw.get('wind_kph', 0)
                    if 'precip_mm' in X_input.columns: X_input['precip_mm'] = hw.get('precip_mm', 0)
                    if 'humidity' in X_input.columns: X_input['humidity'] = hw.get('humidity', 0)
            
            pred_aqi = float(self.models[horizon].predict(X_input)[0])
            pred_aqi = max(0, pred_aqi)  # AQI can't be negative
            
            forecast.append({
                'hours_ahead': horizon,
                'predicted_aqi': round(pred_aqi, 1),
                'aqi_bucket': self._get_aqi_bucket(pred_aqi),
                'aqi_color': self._get_aqi_color(pred_aqi),
            })
        return forecast

    def get_feature_importance(self, feature_names, top_n=15):
        """Get top N important features averaged across all horizons."""
        importance_sum = np.zeros(len(feature_names))
        for horizon, model in self.models.items():
            importance_sum += model.feature_importances_
        avg_importance = importance_sum / len(self.models)

        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': avg_importance
        }).sort_values('importance', ascending=False).head(top_n)

        return importance_df

    def save(self):
        """Save all models and metrics to disk."""
        for horizon, model in self.models.items():
            path = os.path.join(self.model_dir, f'xgb_aqi_{horizon}h.joblib')
            joblib.dump(model, path)
            print(f"[INFO] Saved model: {path}")

        # Save metrics
        metrics_path = os.path.join(self.model_dir, 'metrics.json')
        with open(metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        print(f"[INFO] Saved metrics: {metrics_path}")

    def load(self):
        """Load all models from disk."""
        for horizon in self.HORIZONS:
            path = os.path.join(self.model_dir, f'xgb_aqi_{horizon}h.joblib')
            if os.path.exists(path):
                self.models[horizon] = joblib.load(path)
                print(f"[INFO] Loaded model: {path}")
            else:
                print(f"[WARN] Model not found: {path}")

        # Load metrics
        metrics_path = os.path.join(self.model_dir, 'metrics.json')
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                self.metrics = json.load(f)
                # Convert string keys back to int
                self.metrics = {int(k): v for k, v in self.metrics.items()}

    @staticmethod
    def _filtered_mape(y_true, y_pred, min_aqi=20):
        """Calculate MAPE excluding very low AQI values that distort percentage error."""
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        mask = y_true >= min_aqi
        if mask.sum() == 0:
            return 0.0
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

    @staticmethod
    def _get_aqi_bucket(aqi):
        if aqi <= 50:
            return 'Good'
        elif aqi <= 100:
            return 'Satisfactory'
        elif aqi <= 200:
            return 'Moderate'
        elif aqi <= 300:
            return 'Poor'
        elif aqi <= 400:
            return 'Very Poor'
        else:
            return 'Severe'

    @staticmethod
    def _get_aqi_color(aqi):
        if aqi <= 50:
            return '#00e400'
        elif aqi <= 100:
            return '#ffff00'
        elif aqi <= 200:
            return '#ff7e00'
        elif aqi <= 300:
            return '#ff0000'
        elif aqi <= 400:
            return '#8f3f97'
        else:
            return '#7e0023'
