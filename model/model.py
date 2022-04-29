import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import importlib
import ipdb
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.layers import Dropout, Activation
from sklearn.preprocessing import StandardScaler

hoops_dir = Path(os.path.abspath(__file__)).parent.parent
data_dir = hoops_dir / "data"
model_dir = hoops_dir / "model"
sys.path.append(hoops_dir.as_posix())

def score_model():
    os.makedirs(model_dir / "scores", exist_ok=True)
    