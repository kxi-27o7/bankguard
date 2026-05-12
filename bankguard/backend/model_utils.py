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


def predict(model, features: Dict[str, Any], threshold: Optional[float] = None) -> Tuple[int, Optional[float]]:
    """
    Return (prediction_label, probability_for_positive_or_None).

    - `prediction_label` is int(0/1).
    - `probability` is the probability for the positive class if model
      supports `predict_proba`, otherwise `None`.

    If `threshold` is provided (float between 0 and 1) and the model
    exposes `predict_proba`, the returned label will be computed by
    comparing the positive-class probability against `threshold` instead
    of using `model.predict` (useful when you want a non-default
    decision threshold, e.g. 0.16).
    """
    df = _to_dataframe_row(features)
    prob = None

    # If no threshold requested, prefer the model's own predict()
    if threshold is None:
        pred = model.predict(df)
        # attempt to get probability if available
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(df)
            prob = float(proba[0][1])
        return int(pred[0]), prob

    # threshold provided: require predict_proba
    if not hasattr(model, 'predict_proba'):
        raise ValueError('Model does not support predict_proba; cannot apply threshold')

    proba = model.predict_proba(df)
    prob = float(proba[0][1])
    label = 1 if prob >= float(threshold) else 0
    return int(label), prob
