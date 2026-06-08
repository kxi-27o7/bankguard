"""
Feature engineering utilities for real-time transaction processing.
Converts standard raw JSON payloads into derived features for ML model evaluation.
"""
from typing import Dict, List, Optional, Any
import numpy as np
import math


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Safely performs division, handling ZeroDivision and NaN occurrences."""
    try:
        if b == 0 or b is None or not math.isfinite(a) or not math.isfinite(b):
            return default
        return float(a) / float(b)
    except Exception:
        return default


def _window_stats(amounts: List[float], window: int):
    """Calculates rolling mean and standard deviation for a given transaction window."""
    arr = np.array(amounts[-window:]) if amounts else np.array([])
    if arr.size == 0:
        return 0.0, 0.0, 0
    return float(arr.mean()), float(arr.std(ddof=0)) if arr.size > 1 else 0.0, int(arr.size)


def make_features(tx_raw: Dict[str, Any], history: Optional[Any] = None) -> Dict[str, Any]:
    """Generates engineered ML features from the raw transaction payload and database history."""
    
    # Normalization factor for IDR to base training data alignment
    SCALE_FACTOR = 5.0

    ttype = tx_raw.get('transactionType', '')
    
    raw_old = tx_raw.get('oldBalance', tx_raw.get('oldBalInitiator', 0.0))
    raw_new = tx_raw.get('newBalance', tx_raw.get('newBalInitiator', 0.0))
    
    amount = float(tx_raw.get('amount', 0.0) or 0.0) / SCALE_FACTOR
    old_i = float(raw_old or 0.0) / SCALE_FACTOR
    new_i = float(raw_new or 0.0) / SCALE_FACTOR

    features: Dict[str, Any] = {}

    # Feature: Transaction Type One-Hot Encoding
    types = ["DEBIT", "DEPOSIT", "PAYMENT", "TRANSFER", "WITHDRAWAL"]
    for ty in types:
        features[f"transactionType_{ty}"] = (str(ttype).upper() == ty)

    # Feature: Base Numerics
    features['amount'] = amount
    features['oldBalInitiator'] = old_i
    features['newBalInitiator'] = new_i

    # Feature: Mathematical Ratios
    features['amount_balance_ratio'] = _safe_div(amount, (old_i + 1.0))
    features['balance_error_i'] = float(new_i - (old_i - amount))

    # Compile User History
    if isinstance(history, dict):
        initiator_hist = history.get('initiator', []) or []
    elif isinstance(history, list):
        initiator_hist = history
    else:
        initiator_hist = []

    # Normalize historical amounts to current transaction scale
    init_amounts = [(float(t.get('amount', 0.0) or 0.0) / SCALE_FACTOR) for t in initiator_hist]

    # Feature: Rolling Window Analytics (6, 12, and 24 instances)
    for w in (6, 12, 24):
        avg, _std, cnt = _window_stats(init_amounts, w)
        features[f'INIT_AVG_AMOUNT_TX_{w}'] = avg
        features[f'INIT_AMOUNT_DEV_TX_{w}'] = float(amount - avg)

    return features