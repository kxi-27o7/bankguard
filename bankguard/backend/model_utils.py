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


def _to_dataframe_row(features: Dict[str, Any], model) -> pd.DataFrame:
    """Convert a features dict into a single-row DataFrame, enforcing training column order."""
    df = pd.DataFrame([features])
    
    # Check if the model has the original feature names saved
    if hasattr(model, 'feature_names_in_'):
        expected_columns = model.feature_names_in_
        
        # 1. Add any columns the model expects but are missing from our dictionary (fill with 0)
        for col in expected_columns:
            if col not in df.columns:
                df[col] = 0.0
                
        # 2. Force the DataFrame to use the EXACT column order the model was trained on
        df = df[expected_columns]
        
    return df


def predict(model, features: Dict[str, Any], threshold: Optional[float] = None) -> Tuple[int, Optional[float]]:
    """
    Return (prediction_label, probability_for_positive_or_None).
    """
    # Pass the model into the dataframe converter so it can check feature_names_in_
    df = _to_dataframe_row(features, model)
    
    # Check if the model supports probabilities
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(df)
        prob = float(proba[0][1]) # Probability of class 1 (Fraud)
        
        # If probability is > 25%, flag as fraud
        custom_threshold = 0.25 
        pred = 1 if prob >= custom_threshold else 0
        return pred, prob
    
    else:
        # Fallback if the model doesn't support probabilities
        pred = model.predict(df)
        return int(pred[0]), None
