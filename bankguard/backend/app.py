from cv2 import threshold
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
CORS(app) 

load_dotenv()
db_manager = BankguardManager(os.getenv("MONGO_URL")) 

BASE_DIR = Path(__file__).resolve().parent.parent 
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
    # ... (Keep existing register_user code) ...
    data = request.get_json()
    if not data: return jsonify({'error': 'No JSON data provided'}), 400
    name, email, password = data.get('fullName'), data.get('email'), data.get('password')
    if not name or not email or not password: return jsonify({'error': 'Missing required fields'}), 400
    try:
        new_user_id = db_manager.add_user(name, email, password)
        return jsonify({'success': True, 'userID': new_user_id, 'message': 'Account created successfully'}), 201
    except Exception as e:
        return jsonify({'error': f"Database error: {str(e)}"}), 500

@app.route('/login', methods=['POST'])
def login_user():
    # ... (Keep existing login_user code) ...
    data = request.get_json()
    if not data: return jsonify({'error': 'No JSON data provided'}), 400
    email, password = data.get('email'), data.get('password')
    if not email or not password: return jsonify({'error': 'Missing email or password'}), 400
    try:
        user = db_manager.users.find_one({'email': email})
        if not user: return jsonify({'error': 'Account not found. Please register.'}), 404
        if user.get('password') != password: return jsonify({'error': 'Incorrect password.'}), 401
        return jsonify({'success': True, 'message': 'Login successful', 'userID': user.get('userID'), 'name': user.get('name')}), 200
    except Exception as e:
        return jsonify({'error': f"Database error: {str(e)}"}), 500

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    tx_raw = request.get_json() or {}
    if not tx_raw:
        return jsonify({'error': 'json body required'}), 400

    required = ['initiator', 'amount', 'transactionType', 'oldBalance', 'newBalance']
    missing = [f for f in required if f not in tx_raw]
    if missing:
        return jsonify({'error': 'missing fields', 'fields': missing}), 400

    # FIXED: Force integer conversion for strict MongoDB matching
    try:
        initiator = int(tx_raw.get('initiator', 0))
        tx_raw['initiator'] = initiator # Overwrite it in the raw dict so it saves as an int
    except ValueError:
        initiator = 0

    # 2. Fetch only initiator history
    try:
        initiator_history = list(reversed(db_manager.get_user_history(initiator))) if initiator is not None else []
    except Exception:
        initiator_history = []

    history = {'initiator': initiator_history}

    # 3. Feature engineering
    features = make_features(tx_raw, history=history)

    # 4. Prediction
    if MODEL is None:
        return jsonify({'error': 'model not loaded on server'}), 500

    label, probability = predict(MODEL, features, threshold=0.16)

    # 5. Save raw + features + prediction
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