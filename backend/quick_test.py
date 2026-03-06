"""Quick model test to check per-horizon MAPE."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from preprocess import prepare_dataset, get_feature_columns
from model import AQIPredictionModel
import numpy as np

data_dir = os.path.join(os.path.dirname(__file__), '..')
major_cities = ['Delhi', 'Mumbai', 'Bengaluru', 'Kolkata', 'Chennai',
                'Hyderabad', 'Ahmedabad', 'Pune', 'Lucknow', 'Jaipur',
                'Patna', 'Chandigarh', 'Gurugram', 'Noida']

train_df, test_df, feature_cols, target_cols = prepare_dataset(
    data_dir, city_filter=major_cities
)

X_train = train_df[feature_cols].fillna(0)
X_test = test_df[feature_cols].fillna(0)
y_train_dict = {col: train_df[col] for col in target_cols}
y_test_dict = {col: test_df[col] for col in target_cols}

model = AQIPredictionModel(model_dir=os.path.join(os.path.dirname(__file__), 'models'))
model.train(X_train, y_train_dict, X_val=X_test, y_val_dict=y_test_dict)
model.save()

print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)
all_mapes = []
for h in sorted(model.metrics.keys()):
    m = model.metrics[h]
    status = "PASS" if m['mape'] < 15 else "FAIL"
    print("  %3dh: MAPE=%6.2f%% MAE=%7.2f RMSE=%7.2f [%s]" % (h, m['mape'], m['mae'], m['rmse'], status))
    all_mapes.append(m['mape'])

avg = np.mean(all_mapes)
overall = "PASS" if avg < 15 else "FAIL"
print("\n  Overall Avg MAPE: %.2f%% [%s]" % (avg, overall))
print("  Target: < 15%% MAPE")

# Save training metadata
import json
meta = {
    'cities': major_cities,
    'feature_columns': feature_cols,
    'n_features': len(feature_cols),
    'train_samples': len(X_train),
    'test_samples': len(X_test),
    'train_medians': {k: float(v) for k, v in X_train.median().items()},
}
meta_path = os.path.join(os.path.dirname(__file__), 'models', 'training_meta.json')
with open(meta_path, 'w') as f:
    json.dump(meta, f, indent=2)
print("\nSaved training metadata:", meta_path)
