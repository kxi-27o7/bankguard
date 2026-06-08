import os
import random
import warnings
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

from bankguard_db import BankguardManager
from feature_engineering import make_features
from model_utils import load_model, predict

# Suppress warnings for cleaner logs
warnings.filterwarnings("ignore", category=UserWarning)

app = Flask(__name__)
CORS(app) 

load_dotenv()
db_manager = BankguardManager(os.getenv("MONGO_URL"))

# load the ML model
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'ml' / 'model' / 'model.pkl'
if not MODEL_PATH.exists():
    MODEL_PATH = BASE_DIR / 'ml' / 'model' / 'model.joblib'

try:
    MODEL = load_model(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
except Exception:
    MODEL = None


def seed_initial_transactions(user_id: int, min_amount: float, max_amount: float):
    """Generates a baseline of safe transactions for new user accounts."""
    current_balance = 50000000.00 
    
    for _ in range(30):
        amount = round(random.uniform(min_amount, max_amount), 2)
        new_balance = current_balance - amount
        
        safe_tx = {
            "initiator": user_id,
            "transactionType": "PAYMENT",
            "amount": amount,
            "oldBalance": current_balance,
            "newBalance": new_balance
        }
        
        db_manager.save_transaction_record(
            tx_raw=safe_tx, 
            features={}, 
            prediction=0, 
            probability=0.0
        )
        current_balance = new_balance


@app.route('/', methods=['GET'])
def health_check():
    """API status endpoint."""
    return jsonify({
        "status": "online",
        "message": "BankGuard API is running successfully!",
        "version": "1.0"
    }), 200


@app.route('/register', methods=['POST'])
def register_user():
    """Registers a new user and seeds initial baseline transaction data."""
    data = request.get_json()
    if not data: 
        return jsonify({'error': 'No JSON data provided'}), 400
    
    name = data.get('fullName')
    email = data.get('email')
    password = data.get('password')
    
    avg_min = float(data.get('avgMinTransaction', 150000.0))
    avg_max = float(data.get('avgMaxTransaction', 750000.0))
    
    if not name or not email or not password: 
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        new_user_id = db_manager.add_user(name, email, password)
        seed_initial_transactions(new_user_id, avg_min, avg_max)
        
        return jsonify({
            'success': True, 
            'userID': new_user_id, 
            'message': 'Account created and seeded successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f"Database error: {str(e)}"}), 500


@app.route('/login', methods=['POST'])
def login_user():
    """Authenticates existing users."""
    data = request.get_json()
    if not data: 
        return jsonify({'error': 'No JSON data provided'}), 400
        
    email, password = data.get('email'), data.get('password')
    if not email or not password: 
        return jsonify({'error': 'Missing email or password'}), 400
        
    try:
        user = db_manager.users.find_one({'email': email})
        if not user: 
            return jsonify({'error': 'Account not found. Please register.'}), 404
        if user.get('password') != password: 
            return jsonify({'error': 'Incorrect password.'}), 401
            
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
    """Processes a new transaction through the ML pipeline for fraud evaluation."""
    tx_raw = request.get_json() or {}
    if not tx_raw:
        return jsonify({'error': 'json body required'}), 400

    required = ['initiator', 'amount', 'transactionType', 'oldBalance', 'newBalance']
    missing = [f for f in required if f not in tx_raw]
    if missing:
        return jsonify({'error': 'missing fields', 'fields': missing}), 400

    try:
        initiator = int(tx_raw.get('initiator', 0))
        tx_raw['initiator'] = initiator 
    except ValueError:
        initiator = 0

    try:
        initiator_history = list(reversed(db_manager.get_user_history(initiator))) if initiator is not None else []
    except Exception:
        initiator_history = []

    history = {'initiator': initiator_history}

    if MODEL is None:
        return jsonify({'error': 'model not loaded on server'}), 500

    # Feature Engineering & Prediction Pipeline
    features = make_features(tx_raw, history=history)
    label, probability = predict(MODEL, features, threshold=0.5)

    try:
        saved = db_manager.save_transaction_record(
            tx_raw, 
            features=features, 
            prediction=label, 
            probability=probability, 
            user_id=initiator
        )
    except Exception:
        saved = None

    return jsonify({
        'transactionID': saved.get('transactionID') if saved else None,
        'isFraud': int(label),
        'probability': probability,
        'saved': bool(saved)
    }), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7860)