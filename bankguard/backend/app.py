from pyexpat import model

from flask import Flask, request, jsonify
from flask_cors import CORS
from bankguard_db import BankguardManager # Importing your previous script

app = Flask(__name__)
CORS(app) # This allows the frontend to talk to the backend

# Initialize your manager
db_manager = BankguardManager("ACCESSS INPUT STRING HERE") # Change with passkey to database

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    # 1. Get data sent from HTML
    data = request.json 
    
    # 2. Processing the data
    # This will handle the auto-increment and isFraud prediction
    result = db_manager.process_transaction(data, model=None) # PASS ON MODEL HERE AS WELL
    
    # 3. Send the result back to the frontend
    return jsonify({
        "status": "success",
        "transactionID": result['transactionID'],
        "isFraud": result['isFraud']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)