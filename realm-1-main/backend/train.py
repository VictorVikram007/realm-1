"""
Model Training Script - Multi-Model Support
Trains XGBoost, CNN-LSTM, BiLSTM, or ARIMAX models for AQI forecasting.
"""

import os
import sys

# CRITICAL: Import tensorflow before any other DLL-heavy libraries to avoid initialization conflicts on Windows
try:
    import tensorflow as tf
    # Optional: Suppress TF logging
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
except ImportError:
    pass

import time
import json
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Add backend dir to path before importing local modules
sys.path.insert(0, os.path.dirname(__file__))

from preprocess import prepare_dataset, get_feature_columns
from model import AQIPredictionModel


def get_major_cities():
    return [
        'Delhi', 'Mumbai', 'Bengaluru', 'Kolkata', 'Chennai',
        'Hyderabad', 'Ahmedabad', 'Pune', 'Lucknow', 'Jaipur',
        'Patna', 'Chandigarh', 'Gurugram', 'Noida'
    ]


def prepare_data(data_dir):
    """Load and prepare the common dataset for all model types."""
    major_cities = get_major_cities()
    train_df, test_df, feature_cols, target_cols = prepare_dataset(
        data_dir, city_filter=major_cities
    )

    X_train = train_df[feature_cols].copy().fillna(train_df[feature_cols].median())
    X_test = test_df[feature_cols].copy().fillna(X_train.median())

    y_train_dict = {col: train_df[col] for col in target_cols}
    y_test_dict = {col: test_df[col] for col in target_cols}
    return X_train, X_test, y_train_dict, y_test_dict, feature_cols, major_cities


def print_metrics_summary(model_name, metrics):
    all_mapes = []
    print(f"\n{'=' * 70}")
    print(f"  {model_name} RESULTS")
    print(f"{'=' * 70}")
    for horizon in sorted(metrics.keys(), key=lambda x: int(x)):
        m = metrics[horizon]
        status = "✓ PASS" if m['mape'] < 15 else "✗ FAIL"
        print(f"  {int(horizon):3d}h — MAPE: {m['mape']:6.2f}% | MAE: {m['mae']:7.2f} | RMSE: {m['rmse']:7.2f}  [{status}]")
        all_mapes.append(m['mape'])
    avg = sum(all_mapes) / len(all_mapes) if all_mapes else 0
    status = "✓ PASS" if avg < 15 else "✗ FAIL"
    print(f"\n  Overall Avg MAPE: {avg:.2f}%  [{status}]")
    print(f"  Target: < 15% MAPE")
    print(f"{'=' * 70}")
    return avg


def train_xgboost(X_train, X_test, y_train_dict, y_test_dict, feature_cols, model_dir):
    print(f"\n{'=' * 70}\n  Training XGBoost...\n{'=' * 70}")
    model = AQIPredictionModel(model_dir=model_dir)
    model.train(X_train, y_train_dict, X_val=X_test, y_val_dict=y_test_dict)
    model.save()

    # Feature importance
    imp_df = model.get_feature_importance(feature_cols, top_n=10)
    print("\nTop 10 Feature Importances (XGBoost):")
    for _, row in imp_df.iterrows():
        bar = "█" * int(row['importance'] * 200)
        print(f"  {row['feature']:30s} {row['importance']:.4f}  {bar}")

    return model.metrics


def train_cnn_lstm(X_train, X_test, y_train_dict, y_test_dict, model_dir):
    print(f"\n{'=' * 70}\n  Training CNN-LSTM...\n{'=' * 70}")
    from models.deep_learning import CNNLSTMModel
    model = CNNLSTMModel(model_dir=model_dir)

    # Check if models exist
    from models.deep_learning import HORIZONS
    all_exist = True
    for h in HORIZONS:
        if not os.path.exists(os.path.join(model_dir, f'cnn_lstm_aqi_{h}h.keras')):
            all_exist = False
            break

    if all_exist:
        logger.info("[INFO] CNN-LSTM models found. Loading and evaluating...")
        model.evaluate(X_test, y_test_dict)
    else:
        model.train(X_train, y_train_dict, X_val=X_test, y_val_dict=y_test_dict)
        model.save()

    return model.metrics


def train_bilstm(X_train, X_test, y_train_dict, y_test_dict, model_dir):
    print(f"\n{'=' * 70}\n  Training BiLSTM...\n{'=' * 70}")
    from models.deep_learning import BiLSTMModel
    model = BiLSTMModel(model_dir=model_dir)

    # Check if models exist
    from models.deep_learning import HORIZONS
    all_exist = True
    for h in HORIZONS:
        if not os.path.exists(os.path.join(model_dir, f'bilstm_aqi_{h}h.keras')):
            all_exist = False
            break

    if all_exist:
        logger.info("[INFO] BiLSTM models found. Loading and evaluating...")
        model.evaluate(X_test, y_test_dict)
    else:
        model.train(X_train, y_train_dict, X_val=X_test, y_val_dict=y_test_dict)

    return model.metrics


def train_arimax(X_train, X_test, y_train_dict, y_test_dict, model_dir):
    print(f"\n{'=' * 70}\n  Training ARIMAX...\n{'=' * 70}")
    try:
        from models.statistical import ARIMAXModel
        model = ARIMAXModel(model_dir=model_dir)
        model.train(X_train, y_train_dict, X_val=X_test, y_val_dict=y_test_dict)
        return model.metrics
    except Exception as e:
        logger.error(f"ARIMAX training failed: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description='AirVue Model Training Pipeline')
    parser.add_argument(
        '--model',
        choices=['xgboost', 'cnn_lstm', 'bilstm', 'arimax', 'all'],
        default='xgboost',
        help='Model type to train (default: xgboost)'
    )
    args = parser.parse_args()

    data_dir = os.path.join(os.path.dirname(__file__), '..')
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(model_dir, exist_ok=True)

    print("=" * 70)
    print(f"  AQI PREDICTION - TRAINING PIPELINE | Model: {args.model.upper()}")
    print("=" * 70)

    start_time = time.time()
    models_to_train = ['xgboost', 'cnn_lstm', 'bilstm', 'arimax'] if args.model == 'all' else [args.model]

    X_train, X_test, y_train_dict, y_test_dict, feature_cols, major_cities = prepare_data(data_dir)
    logger.info(f"Data prepared: {len(X_train)} train, {len(X_test)} test rows")

    comparison = {}

    for model_type in models_to_train:
        t0 = time.time()
        if model_type == 'xgboost':
            metrics = train_xgboost(X_train, X_test, y_train_dict, y_test_dict, feature_cols, model_dir)
        elif model_type == 'cnn_lstm':
            metrics = train_cnn_lstm(X_train, X_test, y_train_dict, y_test_dict, model_dir)
        elif model_type == 'bilstm':
            metrics = train_bilstm(X_train, X_test, y_train_dict, y_test_dict, model_dir)
        elif model_type == 'arimax':
            metrics = train_arimax(X_train, X_test, y_train_dict, y_test_dict, model_dir)

        if metrics:
            avg = print_metrics_summary(model_type.upper(), metrics)
            comparison[model_type] = {
                'metrics': {str(k): v for k, v in metrics.items()},
                'avg_mape': round(avg, 2),
                'training_time_s': round(time.time() - t0, 1),
            }

    # Save comparison JSON (Load and Update)
    comp_path = os.path.join(model_dir, 'metrics_comparison.json')
    if os.path.exists(comp_path):
        try:
            with open(comp_path, 'r', encoding='utf-8') as f:
                old_comp = json.load(f)
            old_comp.update(comparison)
            comparison = old_comp
        except Exception as e:
            logger.warning(f"Failed to load existing metrics: {e}")
        
    with open(comp_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=4)
    logger.info(f"Saved/Updated comparison metrics: {comp_path}")

    # Save training metadata
    meta = {
        'cities': major_cities,
        'feature_columns': feature_cols,
        'n_features': len(feature_cols),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'train_medians': X_train.median().to_dict(),
    }
    meta_path = os.path.join(model_dir, 'training_meta.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\n  Total training time: {elapsed:.1f}s")


if __name__ == '__main__':
    main()
