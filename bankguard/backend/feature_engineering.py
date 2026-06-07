"""
Feature engineering utilities for new transactions.

This module provides `make_features(tx_raw, history=None)` which converts the
8 raw input fields into the derived features expected by the trained model.
"""
from typing import Dict, List, Optional, Any
import numpy as np
import math


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        if b == 0 or b is None or math.isfinite(a) is False or math.isfinite(b) is False:
            return default
        return float(a) / float(b)
    
    except Exception:
        return default


def _window_stats(amounts: List[float], window: int):
    arr = np.array(amounts[-window:]) if amounts else np.array([])
    if arr.size == 0:
        return 0.0, 0.0, 0
    return float(arr.mean()), float(arr.std(ddof=0)) if arr.size > 1 else 0.0, int(arr.size)


def make_features(tx_raw: Dict[str, Any], history: Optional[Any] = None) -> Dict[str, Any]:
    
    # Assuming training data was in USD, 1 USD = ~15,000 IDR
    SCALE_FACTOR = 5.0

    # Extract raw fields with safe defaults
    ttype = tx_raw.get('transactionType', '')
    
    # Check for both the new keys ('oldBalance') and the old keys ('oldBalInitiator')
    raw_old = tx_raw.get('oldBalance', tx_raw.get('oldBalInitiator', 0.0))
    raw_new = tx_raw.get('newBalance', tx_raw.get('newBalInitiator', 0.0))
    
    amount = float(tx_raw.get('amount', 0.0) or 0.0) / SCALE_FACTOR
    old_i = float(raw_old or 0.0) / SCALE_FACTOR
    new_i = float(raw_new or 0.0) / SCALE_FACTOR

    features: Dict[str, Any] = {}

    # one-hot encode transaction type
    types = ["DEBIT", "DEPOSIT", "PAYMENT", "TRANSFER", "WITHDRAWAL"]
    for ty in types:
        features[f"transactionType_{ty}"] = (str(ttype).upper() == ty)

    # basic numeric features
    features['amount'] = amount
    features['oldBalInitiator'] = old_i
    features['newBalInitiator'] = new_i

    # ratios and error terms
    features['amount_balance_ratio'] = _safe_div(amount, (old_i + 1.0))
    features['balance_error_i'] = float(new_i - (old_i - amount))

    # prepare history lists
    initiator_hist = None
    if history is None:
        initiator_hist = []
    elif isinstance(history, dict):
        initiator_hist = history.get('initiator', []) or []
    elif isinstance(history, list):
        initiator_hist = history
    else:
        initiator_hist = []

    # FIXED: Apply SCALE_FACTOR to historical amounts so they match the current amount
    init_amounts = [(float(t.get('amount', 0.0) or 0.0) / SCALE_FACTOR) for t in initiator_hist]

    # INIT stats for windows 6,12,24
    # - INIT_AVG_AMOUNT_TX_{w}: rolling mean over last `w` transactions (if any)
    # - INIT_AMOUNT_DEV_TX_{w}: deviation of current `amount` from that rolling mean
    for w in (6, 12, 24):
        avg, _std, cnt = _window_stats(init_amounts, w)
        features[f'INIT_AVG_AMOUNT_TX_{w}'] = avg
        features[f'INIT_AMOUNT_DEV_TX_{w}'] = float(amount - avg)

    return features