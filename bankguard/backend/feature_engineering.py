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
    SCALE_FACTOR = 5.0

    # Use the new field names
    amount = float(tx_raw.get('amount', 0.0) or 0.0) / SCALE_FACTOR
    old_i = float(tx_raw.get('oldBalance', 0.0) or 0.0) / SCALE_FACTOR
    new_i = float(tx_raw.get('newBalance', 0.0) or 0.0) / SCALE_FACTOR

    features: Dict[str, Any] = {}

    # Transaction Type is ignored for feature generation based on new rules

    # Basic numeric features 
    features['amount'] = amount
    features['oldBalance'] = old_i
    features['newBalance'] = new_i

    # Derived logic
    features['amount_balance_ratio'] = _safe_div(amount, (old_i + 1.0))
    features['balance_error'] = float(new_i - (old_i - amount))

    # Initiator history processing
    initiator_hist = []
    if isinstance(history, dict):
        initiator_hist = history.get('initiator', []) or []
    elif isinstance(history, list):
        initiator_hist = history

    init_amounts = [float(t.get('amount', 0.0) or 0.0) for t in initiator_hist]

    # INIT stats for windows 6,12,24
    # - INIT_AVG_AMOUNT_TX_{w}: rolling mean over last `w` transactions (if any)
    # - INIT_AMOUNT_DEV_TX_{w}: deviation of current `amount` from that rolling mean
    for w in (6, 12, 24):
        avg, _std, cnt = _window_stats(init_amounts, w)
        features[f'INIT_AVG_AMOUNT_TX_{w}'] = avg
        features[f'INIT_AMOUNT_DEV_TX_{w}'] = float(amount - avg)

    return features