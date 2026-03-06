"""
Data Preprocessing & Feature Engineering for AQI Prediction
Loads city_hour.csv, cleans data, engineers temporal and lag features,
and prepares train/test splits for multi-horizon forecasting.
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ── Indian NAQI Sub-Index Breakpoints ──────────────────────────────────
# Format: (C_low, C_high, I_low, I_high)
BREAKPOINTS = {
    'PM2.5': [(0,30,0,50),(31,60,51,100),(61,90,101,200),(91,120,201,300),(121,250,301,400),(251,500,401,500)],
    'PM10':  [(0,50,0,50),(51,100,51,100),(101,250,101,200),(251,350,201,300),(351,430,301,400),(431,500,401,500)],
    'NO2':   [(0,40,0,50),(41,80,51,100),(81,180,101,200),(181,280,201,300),(281,400,301,400),(401,500,401,500)],
    'SO2':   [(0,40,0,50),(41,80,51,100),(81,380,101,200),(381,800,201,300),(801,1600,301,400),(1601,2000,401,500)],
    'CO':    [(0,1,0,50),(1.1,2,51,100),(2.1,10,101,200),(10.1,17,201,300),(17.1,34,301,400),(34.1,50,401,500)],
    'O3':    [(0,50,0,50),(51,100,51,100),(101,168,101,200),(169,208,201,300),(209,748,301,400),(749,1000,401,500)],
    'NH3':   [(0,200,0,50),(201,400,51,100),(401,800,101,200),(801,1200,201,300),(1201,1800,301,400),(1801,2400,401,500)],
}


def calc_sub_index(value, pollutant):
    """Calculate AQI sub-index for a single pollutant value."""
    if pd.isna(value) or pollutant not in BREAKPOINTS:
        return np.nan
    for c_lo, c_hi, i_lo, i_hi in BREAKPOINTS[pollutant]:
        if c_lo <= value <= c_hi:
            return ((i_hi - i_lo) / (c_hi - c_lo)) * (value - c_lo) + i_lo
    return np.nan


def calculate_aqi(row):
    """Calculate AQI as max of all available sub-indices (Indian NAQI standard)."""
    pollutants = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NH3']
    sub_indices = []
    for p in pollutants:
        if p in row.index and not pd.isna(row[p]):
            si = calc_sub_index(row[p], p)
            if not pd.isna(si):
                sub_indices.append(si)
    return max(sub_indices) if len(sub_indices) >= 1 else np.nan


def get_dominant_pollutant(row):
    """Identify the dominant pollutant (highest sub-index)."""
    pollutants = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NH3']
    max_si, dominant = -1, None
    for p in pollutants:
        if p in row.index and not pd.isna(row[p]):
            si = calc_sub_index(row[p], p)
            if not pd.isna(si) and si > max_si:
                max_si, dominant = si, p
    return dominant


def load_and_clean(data_dir):
    """Load city_hour.csv, clean, and return a DataFrame."""
    filepath = os.path.join(data_dir, 'city_hour.csv')
    print(f"[INFO] Loading {filepath}...")
    df = pd.read_csv(filepath, parse_dates=['Datetime'])
    print(f"[INFO] Raw shape: {df.shape}")

    # Sort by city and datetime
    df = df.sort_values(['City', 'Datetime']).reset_index(drop=True)

    # Pollutant columns
    pollutant_cols = ['PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3',
                      'Benzene', 'Toluene', 'Xylene']

    # Drop rows where more than 50% of pollutant columns are missing
    threshold = len(pollutant_cols) * 0.5
    df = df.dropna(subset=pollutant_cols, thresh=int(threshold))
    print(f"[INFO] After dropping sparse rows: {df.shape}")

    # Forward fill then backward fill within each city
    df[pollutant_cols] = df.groupby('City')[pollutant_cols].transform(
        lambda x: x.ffill().bfill()
    )

    # Calculate AQI where missing
    mask = df['AQI'].isna()
    if mask.any():
        print(f"[INFO] Calculating AQI for {mask.sum()} rows with missing AQI...")
        df.loc[mask, 'AQI'] = df.loc[mask].apply(calculate_aqi, axis=1)

    # Drop remaining rows without AQI
    df = df.dropna(subset=['AQI'])
    print(f"[INFO] After AQI cleanup: {df.shape}")

    # Clip extreme AQI outliers (beyond 500 is measurement error)
    df['AQI'] = df['AQI'].clip(lower=1, upper=500)

    # --- Step 4: Enhanced Anomaly Detection ---
    # Remove sudden, non-physical spikes (e.g. > 150 AQI change in 1 hour)
    df = df.sort_values(['City', 'Datetime'])
    df['AQI_diff'] = df.groupby('City')['AQI'].diff().abs()
    anomaly_mask = df['AQI_diff'] > 150
    if anomaly_mask.any():
        print(f"[INFO] Removing {anomaly_mask.sum()} non-physical AQI spikes (>150/hr)")
        df = df[~anomaly_mask]
    df = df.drop(columns=['AQI_diff'])

    return df


def add_temporal_features(df):
    """Add temporal features from the Datetime column."""
    df = df.copy()
    df['hour'] = df['Datetime'].dt.hour
    df['day_of_week'] = df['Datetime'].dt.dayofweek
    df['month'] = df['Datetime'].dt.month
    df['day_of_year'] = df['Datetime'].dt.dayofyear
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    # Cyclical encoding for hour (helps capture circular patterns)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    # Season (India-specific)
    def get_season(month):
        if month in [12, 1, 2]:
            return 0  # Winter
        elif month in [3, 4, 5]:
            return 1  # Summer
        elif month in [6, 7, 8, 9]:
            return 2  # Monsoon
        else:
            return 3  # Post-Monsoon

    df['season'] = df['month'].apply(get_season)

    # City label encoding for city-specific patterns
    cities = sorted(df['City'].unique())
    city_map = {c: i for i, c in enumerate(cities)}
    df['city_encoded'] = df['City'].map(city_map)

    return df


def add_lag_and_rolling_features(df, target_col='AQI'):
    """Add lag features and rolling statistics per city."""
    df = df.copy()

    lag_hours = [1, 2, 3, 6, 12, 24, 48]
    rolling_windows = [6, 12, 24, 48, 72]

    groups = []
    for city, group in df.groupby('City'):
        group = group.sort_values('Datetime').copy()

        # Lag features
        for lag in lag_hours:
            group[f'{target_col}_lag_{lag}'] = group[target_col].shift(lag)

        # Difference features (AQI change rate)
        group['AQI_diff_1'] = group[target_col].diff(1)
        group['AQI_diff_6'] = group[target_col].diff(6)
        group['AQI_diff_24'] = group[target_col].diff(24)

        # EWM (exponential weighted mean) — captures recent trend
        group['AQI_ewm_12'] = group[target_col].ewm(span=12, min_periods=1).mean()
        group['AQI_ewm_24'] = group[target_col].ewm(span=24, min_periods=1).mean()
        group['AQI_ewm_36'] = group[target_col].ewm(span=36, min_periods=1).mean()
        group['AQI_ewm_48'] = group[target_col].ewm(span=48, min_periods=1).mean()
        group['AQI_ewm_72'] = group[target_col].ewm(span=72, min_periods=1).mean()

        # Same-hour yesterday & 2 days ago (captures daily patterns)
        group['AQI_same_hour_1d'] = group[target_col].shift(24)
        group['AQI_same_hour_2d'] = group[target_col].shift(48)

        # Weekly average (helps 24h-48h predictions)
        group['AQI_rolling_mean_168'] = group[target_col].rolling(168, min_periods=24).mean()

        # Rolling features on AQI
        for window in rolling_windows:
            group[f'{target_col}_rolling_mean_{window}'] = group[target_col].rolling(window, min_periods=1).mean()
            group[f'{target_col}_rolling_std_{window}'] = group[target_col].rolling(window, min_periods=1).std()

        # Additional interactions (user requested)
        group['AQI_inter_ewm12_rm6'] = group['AQI_ewm_12'] * group[f'{target_col}_rolling_mean_6']
        group['AQI_inter_lag1_rm24'] = group[f'{target_col}_lag_1'] * group[f'{target_col}_rolling_mean_24']

        # Rolling features on PM2.5
        if 'PM2.5' in group.columns:
            for window in rolling_windows:
                group[f'PM25_rolling_mean_{window}'] = group['PM2.5'].rolling(window, min_periods=1).mean()

        # Rolling features on PM10
        if 'PM10' in group.columns:
            for window in rolling_windows:
                group[f'PM10_rolling_mean_{window}'] = group['PM10'].rolling(window, min_periods=1).mean()

        # Pollutant ratios
        if 'PM2.5' in group.columns and 'PM10' in group.columns:
            group['PM25_PM10_ratio'] = group['PM2.5'] / group['PM10'].replace(0, np.nan)

        if 'NO2' in group.columns and 'NOx' in group.columns:
            group['NO2_NOx_ratio'] = group['NO2'] / group['NOx'].replace(0, np.nan)

        groups.append(group)

    df = pd.concat(groups, ignore_index=True)

    # Fill NaN ratios
    df['PM25_PM10_ratio'] = df['PM25_PM10_ratio'].fillna(df['PM25_PM10_ratio'].median())
    df['NO2_NOx_ratio'] = df['NO2_NOx_ratio'].fillna(df['NO2_NOx_ratio'].median())

    return df


def create_multi_horizon_targets(df, horizons=[1, 6, 12, 24, 48]):
    """Create target variables for multi-horizon forecasting."""
    df = df.copy()
    groups = []
    for city, group in df.groupby('City'):
        group = group.sort_values('Datetime').copy()
        for h in horizons:
            group[f'AQI_target_{h}h'] = group['AQI'].shift(-h)
        groups.append(group)
    return pd.concat(groups, ignore_index=True)


def get_feature_columns():
    """Return the list of feature column names used by the model."""
    pollutant_features = ['PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3',
                          'Benzene', 'Toluene', 'Xylene']
    temporal_features = ['hour', 'day_of_week', 'month', 'day_of_year', 'is_weekend', 'season',
                         'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'city_encoded']
    lag_features = [f'AQI_lag_{h}' for h in [1, 2, 3, 6, 12, 24, 48]]
    rolling_features = (
        [f'AQI_rolling_mean_{w}' for w in [6, 12, 24, 48, 72]] +
        [f'AQI_rolling_std_{w}' for w in [6, 12, 24, 48, 72]] +
        [f'PM25_rolling_mean_{w}' for w in [6, 12, 24, 48, 72]] +
        [f'PM10_rolling_mean_{w}' for w in [6, 12, 24, 48, 72]]
    )
    ratio_features = ['PM25_PM10_ratio', 'NO2_NOx_ratio']
    diff_features = ['AQI_diff_1', 'AQI_diff_6', 'AQI_diff_24']
    ewm_features = ['AQI_ewm_12', 'AQI_ewm_24', 'AQI_ewm_36', 'AQI_ewm_48', 'AQI_ewm_72']
    daily_features = ['AQI_same_hour_1d', 'AQI_same_hour_2d', 'AQI_rolling_mean_168']
    interaction_features = ['AQI_inter_ewm12_rm6', 'AQI_inter_lag1_rm24']

    return (pollutant_features + temporal_features + lag_features + rolling_features +
            ratio_features + diff_features + ewm_features + daily_features + interaction_features)


def prepare_dataset(data_dir, city_filter=None):
    """Full pipeline: load → clean → features → targets → train/test split."""
    df = load_and_clean(data_dir)

    if city_filter:
        df = df[df['City'].isin(city_filter)]
        print(f"[INFO] Filtered to cities: {city_filter}, shape: {df.shape}")

    df = add_temporal_features(df)
    df = add_lag_and_rolling_features(df)
    df = create_multi_horizon_targets(df)

    # Drop rows with NaN in lag features (first 48 hours per city)
    feature_cols = get_feature_columns()
    horizons = [1, 6, 12, 24, 48]
    target_cols = [f'AQI_target_{h}h' for h in horizons]

    df = df.dropna(subset=feature_cols + target_cols)
    print(f"[INFO] Final dataset shape: {df.shape}")

    # Temporal train/test split (80/20)
    df = df.sort_values('Datetime')
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    print(f"[INFO] Train: {train_df.shape}, Test: {test_df.shape}")
    print(f"[INFO] Train period: {train_df['Datetime'].min()} to {train_df['Datetime'].max()}")
    print(f"[INFO] Test period:  {test_df['Datetime'].min()} to {test_df['Datetime'].max()}")

    return train_df, test_df, feature_cols, target_cols


if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..')
    train_df, test_df, feature_cols, target_cols = prepare_dataset(data_dir)
    print(f"\nFeature columns ({len(feature_cols)}):")
    for f in feature_cols:
        print(f"  - {f}")
    print(f"\nTarget columns: {target_cols}")
