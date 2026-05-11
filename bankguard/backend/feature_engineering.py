"""
Feature engineering utilities for new transactions.

This module provides `make_features(tx_raw, history=None)` which converts the
8 raw input fields into the derived features expected by the trained model.

Notes:
- `history` may be either a list of prior transaction dicts or a dict with
  optional keys `initiator` and `recipient` mapping to lists of transactions.
- If historical data is not available, INIT_/RECIP_ features will be zeros.
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
    """
    Produce derived features from the provided raw transaction input.

    tx_raw must include at least these keys:
    - transactionType, amount, initiator, oldBalInitiator, newBalInitiator,
      recipient, oldBalRecipient, newBalRecipient

    `history` (optional) can be:
    - None: all INIT_/RECIP_ features set to sensible defaults (zeros)
    - list of transaction dicts (assumed to be initiator history)
    - dict with keys `initiator` and/or `recipient` mapping to lists of tx dicts

    Returns a dict containing all features listed in your model spec.
    """
    # Extract raw fields with safe defaults
    ttype = tx_raw.get('transactionType', '')
    amount = float(tx_raw.get('amount', 0.0) or 0.0)
    old_i = float(tx_raw.get('oldBalInitiator', 0.0) or 0.0)
    new_i = float(tx_raw.get('newBalInitiator', 0.0) or 0.0)
    old_r = float(tx_raw.get('oldBalRecipient', 0.0) or 0.0)
    new_r = float(tx_raw.get('newBalRecipient', 0.0) or 0.0)

    features: Dict[str, Any] = {}

    # one-hot encode transaction type (assumes these categories from training)
    types = ["DEBIT", "DEPOSIT", "PAYMENT", "TRANSFER", "WITHDRAWAL"]
    for ty in types:
        features[f"transactionType_{ty}"] = (str(ttype).upper() == ty)

    # basic numeric features
    features['amount'] = amount
    features['oldBalInitiator'] = old_i
    features['newBalInitiator'] = new_i
    features['oldBalRecipient'] = old_r
    features['newBalRecipient'] = new_r

    # ratios and error terms (mirror logic used in the training notebook)
    # amount_balance_ratio := amount / (oldBalInitiator + 1)
    features['amount_balance_ratio'] = _safe_div(amount, (old_i + 1.0))

    # balance_increase_ratio := amount / (oldBalRecipient + 1e-5)
    features['balance_increase_ratio'] = _safe_div(amount, (old_r + 1e-5))

    # neg_balance_i := both old and new initiator balances are negative
    features['neg_balance_i'] = int((old_i < 0) and (new_i < 0))

    # balance_error_i = actual new - expected new (expected new = old - amount)
    features['balance_error_i'] = float(new_i - (old_i - amount))

    # balance_error_r = actual new recipient - expected new recipient (expected = old + amount)
    features['balance_error_r'] = float(new_r - (old_r + amount))

    # prepare history lists
    initiator_hist = None
    recipient_hist = None
    if history is None:
        initiator_hist = []
        recipient_hist = []
    elif isinstance(history, dict):
        initiator_hist = history.get('initiator', []) or []
        recipient_hist = history.get('recipient', []) or []
    elif isinstance(history, list):
        initiator_hist = history
        recipient_hist = []
    else:
        initiator_hist = []
        recipient_hist = []

    # extract amounts and fraud flags from histories
    init_amounts = [float(t.get('amount', 0.0) or 0.0) for t in initiator_hist]
    recip_amounts = [float(t.get('amount', 0.0) or 0.0) for t in recipient_hist]
    init_labels = [int(t.get('isFraud', 0) or 0) for t in initiator_hist]
    recip_labels = [int(t.get('isFraud', 0) or 0) for t in recipient_hist]

    # INIT stats for windows 6,12,24
    # - INIT_AVG_AMOUNT_TX_{w}: rolling mean over last `w` transactions (if any)
    # - INIT_AMOUNT_DEV_TX_{w}: deviation of current `amount` from that rolling mean
    # - INIT_TX_COUNT_STEP_{w}: prefer step-based count when `step` is available in history
    for w in (6, 12, 24):
        avg, _std, cnt = _window_stats(init_amounts, w)
        features[f'INIT_AVG_AMOUNT_TX_{w}'] = avg
        # in ipynb this is computed as amount - rolling_mean (per-row deviation)
        features[f'INIT_AMOUNT_DEV_TX_{w}'] = float(amount - avg)

        # try to compute step-based counts if history items include `step` and tx_raw has `step`
        tx_count_step = cnt
        try:
            current_step = int(tx_raw.get('step'))
            # collect steps from history if present
            steps = [int(t.get('step')) for t in initiator_hist if t.get('step') is not None]
            if steps:
                tx_count_step = sum(1 for s in steps if (s >= current_step - w) and (s <= current_step))
        except Exception:
            # fallback to count of last `w` transactions
            tx_count_step = cnt

        features[f'INIT_TX_COUNT_STEP_{w}'] = int(tx_count_step)

    # RECIP stats (risk = fraction of frauds in window; tx count likewise)
    # recipient risk features. ipynb shifts fraud labels by a delay to avoid leakage;
    # for online prediction we approximate that by excluding the last `delay` recipient records.
    delay = 6
    for w in (6, 12, 24):
        _, _rec_dev, rec_cnt = _window_stats(recip_amounts, w)

        # Exclude most recent `delay` recipient records (if available) to mimic shift(delay)
        if len(recip_labels) > delay:
            labels_to_use = recip_labels[:-delay][-w:]
        else:
            labels_to_use = recip_labels[-w:]

        rec_risk = 0.0
        if len(labels_to_use) > 0:
            rec_risk = float(sum(labels_to_use) / len(labels_to_use))

        features[f'RECIP_RISK_{w}'] = rec_risk
        features[f'RECIP_TX_COUNT_{w}'] = float(len(labels_to_use))

    return features
