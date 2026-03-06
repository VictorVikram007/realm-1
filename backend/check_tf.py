import sys
import os
import traceback

print("Python executable:", sys.executable)
print("Current directory:", os.getcwd())

try:
    import tensorflow as tf
    print("TensorFlow version:", tf.__version__)
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense
    print("Keras imported successfully")
except Exception as e:
    print("ERROR: TensorFlow/Keras import failed")
    traceback.print_exc()
