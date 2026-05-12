from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Local backend modules
from bankguard_db import BankguardManager
from feature_engineering import make_features
from model_utils import load_model, predict

app = Flask(__name__)
CORS(app)  # This allows the frontend to talk to the backend

# Initialize your manager
db_manager = BankguardManager("ACCESSS INPUT STRING HERE") # Change with passkey to database

# Load model at startup if available
MODEL = None
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ml', 'model', 'model.pkl'))
if not os.path.exists(MODEL_PATH):
    alt = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ml', 'model', 'model.joblib'))
    if os.path.exists(alt):
        MODEL_PATH = alt

try:
    if os.path.exists(MODEL_PATH):
        MODEL = load_model(MODEL_PATH)
except Exception:
    MODEL = None


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    """Full pipeline:
    1) accept raw tx JSON from frontend
    2) fetch initiator/recipient history from DB (reverse to chronological)
    3) compute features via `make_features`
    4) run model.predict / predict_proba
    5) save raw + features + prediction via `save_transaction_record`
    """
    tx_raw = request.get_json() or {}
    if not tx_raw:
        return jsonify({'error': 'json body required'}), 400

    # Validate minimal fields
    required = ['initiator', 'recipient', 'amount', 'transactionType',
                'oldBalInitiator', 'newBalInitiator', 'oldBalRecipient', 'newBalRecipient']
    missing = [f for f in required if f not in tx_raw]
    if missing:
        return jsonify({'error': 'missing fields', 'fields': missing}), 400

    initiator = tx_raw.get('initiator')
    recipient = tx_raw.get('recipient')

    # Fetch histories from DB. We reverse results to chronological (oldest->newest)
    try:
        initiator_history = list(reversed(db_manager.get_user_history(initiator))) if initiator is not None else []
    except Exception:
        initiator_history = []
    try:
        recip_raw = list(db_manager.transactions.find({'recipient': recipient}).sort('transactionID', -1)) if recipient is not None else []
        recipient_history = list(reversed(recip_raw))
    except Exception:
        recipient_history = []

    history = {'initiator': initiator_history, 'recipient': recipient_history}

    # Feature engineering
    features = make_features(tx_raw, history=history)

    # Prediction
    if MODEL is None:
        # return informative error; alternatively, you can still save record with prediction=None
        return jsonify({'error': 'model not loaded on server'}), 500

    label, probability = predict(MODEL, features, threshold=0.16)

    # Save raw + features + prediction
    try:
        saved = db_manager.save_transaction_record(tx_raw, features=features, prediction=label, probability=probability, user_id=initiator)
    except Exception:
        saved = None

    return jsonify({'transactionID': saved.get('transactionID') if saved else None,
                    'isFraud': int(label),
                    'probability': probability,
                    'saved': bool(saved)}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)