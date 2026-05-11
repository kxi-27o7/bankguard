from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
import os

# Local backend modules
from bankguard_db import BankguardManager
from feature_engineering import make_features
from model_utils import load_model, predict

app = Flask(__name__)
CORS(app)  # This allows the frontend to talk to the backend

# Initialize your manager
load_dotenv()
db_manager = BankguardManager(os.getenv("MONGO_URL")) # Change with passkey to database

# Load model at startup if available
BASE_DIR = Path(__file__).resolve().parent.parent # Finds the parent folder
MODEL_PATH = BASE_DIR / 'ml' / 'model' / 'model.pkl'
if not MODEL_PATH.exists():
    MODEL_PATH = BASE_DIR / 'ml' / 'model' / 'model.joblib'

try:
    if os.path.exists(MODEL_PATH):
        MODEL = load_model(MODEL_PATH)
    
except Exception:
    MODEL = None


@app.route('/register', methods=['POST'])
def register_user():
    """Endpoint to handle new user registrations"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    name = data.get('fullName')
    email = data.get('email')
    password = data.get('password')

    # Basic backend validation
    if not name or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        # This will auto-increment the ID and save to MongoDB
        new_user_id = db_manager.add_user(name, email, password)
        
        return jsonify({
            'success': True, 
            'userID': new_user_id,
            'message': 'Account created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f"Database error: {str(e)}"}), 500


@app.route('/login', methods=['POST'])
def login_user():
    """Endpoint to handle user logins"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    try:
        # Search the database for a user with this email
        user = db_manager.users.find_one({'email': email})

        # If user doesn't exist
        if not user:
            return jsonify({'error': 'Account not found. Please register.'}), 404

        # If password doesn't match
        if user.get('password') != password:
            return jsonify({'error': 'Incorrect password.'}), 401

        # Success!
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'userID': user.get('userID'),
            'name': user.get('name')
        }), 200

    except Exception as e:
        return jsonify({'error': f"Database error: {str(e)}"}), 500


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
        # Use the new cleaner method
        recipient_history = list(reversed(db_manager.get_recipient_history(recipient))) if recipient is not None else []
    except Exception:
        recipient_history = []

    history = {'initiator': initiator_history, 'recipient': recipient_history}

    # Feature engineering
    features = make_features(tx_raw, history=history)

    # Prediction
    if MODEL is None:
        # return informative error; alternatively, you can still save record with prediction=None
        return jsonify({'error': 'model not loaded on server'}), 500

    label, probability = predict(MODEL, features)

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