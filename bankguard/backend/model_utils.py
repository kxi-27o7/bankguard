"""
Model evaluation utilities for BankGuard.
Handles model loading, dataframe formatting, and dynamic probability evaluations.
"""
from typing import Dict, Any, Optional, Tuple
import joblib
import pandas as pd

def load_model(path: str):
    """Load and return a trained model (joblib or pickle format)."""
    return joblib.load(path)

def _to_dataframe_row(features: Dict[str, Any], model) -> pd.DataFrame:
    """Converts a feature dictionary into a DataFrame, strictly enforcing training column architecture."""
    df = pd.DataFrame([features])
    
    if hasattr(model, 'feature_names_in_'):
        expected_columns = list(model.feature_names_in_)
        # Safely align data structure, padding missing legacy fields with 0.0
        df = df.reindex(columns=expected_columns, fill_value=0.0)
        
    return df

def predict(model, features: Dict[str, Any], threshold: Optional[float] = None) -> Tuple[int, Optional[float]]:
    """
    Evaluates feature data against the model.
    Returns a tuple containing the (prediction_label, probability_score).
    """
    df = _to_dataframe_row(features, model)
    active_threshold = threshold if threshold is not None else 0.50
    
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(df)
        
        # Dynamically locate the positive (Fraud) class index
        if hasattr(model, 'classes_'):
            classes = list(model.classes_)
            fraud_index = classes.index(1) if 1 in classes else 1
            prob = float(proba[0][fraud_index])
        else:
            prob = float(proba[0][1])
            
        pred = 1 if prob >= active_threshold else 0
        return pred, prob
    
    else:
        # Fallback for models that do not support probability distributions
        pred = model.predict(df)
        return int(pred[0]), None