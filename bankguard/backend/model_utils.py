"""
Simple model loader and prediction helpers.

This module loads a scikit-learn compatible model (pickle / joblib) and
provides `predict` and `predict_proba_if_available` helpers that accept a
features dict (single sample) and return the model outputs.

Keep feature dict keys consistent with the training-time feature names/order.
"""
from typing import Dict, Any, Optional, Tuple
import joblib
import pandas as pd


def load_model(path: str):
    """Load and return a trained model (joblib or pickle file)."""
    return joblib.load(path)


def _to_dataframe_row(features: Dict[str, Any]) -> pd.DataFrame:
    """Convert a features dict into a single-row DataFrame for model input."""
    # Model was trained with a consistent set of column names. Create a
    # one-row DataFrame. Caller must ensure keys match training features.
    return pd.DataFrame([features])


def predict(model, features: Dict[str, Any]) -> Tuple[int, Optional[float]]:
    """
    Return (prediction_label, probability_for_positive_or_None).

    - `prediction_label` is int(0/1).
    - `probability` is the probability for the positive class if model
      supports `predict_proba`, otherwise `None`.
    """
    df = _to_dataframe_row(features)
    pred = model.predict(df)
    prob = None
    # Some models expose predict_proba
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(df)
        # assume positive class is column 1
        prob = float(proba[0][1])
    return int(pred[0]), prob
