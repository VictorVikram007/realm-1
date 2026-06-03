import sys, os, json
sys.path.insert(0, r'c:/Users/Vikram/OneDrive/Desktop/DS/backend')
from model import AQIPredictionModel

m = AQIPredictionModel(r'c:/Users/Vikram/OneDrive/Desktop/DS/backend/models')
m.load()

with open(r'c:/Users/Vikram/OneDrive/Desktop/DS/backend/models/training_meta.json') as f:
    meta = json.load(f)
    
imp = m.get_feature_importance(meta['feature_columns'], top_n=15)
print(imp.to_string())
