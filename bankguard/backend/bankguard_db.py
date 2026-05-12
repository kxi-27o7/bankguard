from pymongo import MongoClient, ReturnDocument
from datetime import datetime
from typing import Optional, Dict

class BankguardManager:
    def __init__(self, connection_string):
        # Use the connection string with the tlsInsecure=True flag we discussed
        self.client = MongoClient(connection_string)
        self.db = self.client.BankguardDB
        self.users = self.db.users
        self.transactions = self.db.transactions
        self.counters = self.db.counters


    def _get_next_id(self, counter_name):
        """Internal method to handle auto-increment logic."""
        counter = self.counters.find_one_and_update(
            {"_id": counter_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return counter['seq']
    

    def add_user(self, name, email, password):
        """Creates a new user with a unique userID."""
        user_id = self._get_next_id("userid")
        user_doc = {
            "userID": user_id,
            "name": name,
            "email": email,
            "password": password
        }
        self.users.insert_one(user_doc)
        return user_id


    def get_user_history(self, user_id):
        """Fetches the most recent transactions for a specific user ID."""
        return list(self.transactions.find({"initiator": user_id}).sort("transactionID", -1))
    
    def get_recipient_history(self, recipient_id):
        """Fetches the most recent transactions for a specific recipient."""
        return list(self.transactions.find({"recipient": recipient_id}).sort("transactionID", -1))
    
    
    # This function is moved to app.py (might be deleted entirely from here)
    # def process_transaction(self, tx_data, model=None):
    #     """
    #     Logic: Checks history -> Predicts Fraud -> Saves to DB
    #     tx_data should contain: initiator, recipient, amount, transactionType
    #     """
    #     initiator_id = tx_data['initiator']
        
    #     # 1. Check for previous transactions from the getter
    #     history = self.get_user_history(initiator_id)
        
    #     # 2. Assume not fraud if it's the first transaction
    #     if not history:
    #         is_fraud_prediction = False
    #         old_balance = 1000.00 # Standard starting mockup balance (change if necessary)

    #     else:
    #         # Get the most recent balance from the latest transaction
    #         old_balance = history[0]['newBalInitiator']
            
    #         # 3. Machine Learning Prediction
    #         if model:
    #             # Prepare features for your Random Forest (Example format)
    #             features = [[tx_data['amount'], old_balance, len(history)]]
    #             is_fraud_prediction = bool(model.predict(features)[0])

    #         else:
    #             is_fraud_prediction = False # Fallback if model isn't loaded

    #     # 4. Final Document Construction
    #     tx_id = self._get_next_id("transactionid")
    #     # Build base transaction document
    #     final_doc = {
    #         "transactionID": tx_id,
    #         "transactionType": tx_data.get('transactionType'),
    #         "amount": float(tx_data.get('amount', 0.0)),
    #         "initiator": initiator_id,
    #         "oldBalInitiator": float(old_balance),
    #         "newBalInitiator": float(old_balance - tx_data.get('amount', 0.0)),
    #         "recipient": tx_data.get('recipient'),
    #         "oldBalRecipient": float(tx_data.get('oldBalRecipient', 0.0)),
    #         "newBalRecipient": float(tx_data.get('newBalRecipient', tx_data.get('amount', 0.0))),
    #         "isFraud": bool(is_fraud_prediction),
    #         "created_at": datetime.utcnow()
    #     }

    #     # Insert the transaction document into MongoDB
    #     self.transactions.insert_one(final_doc)
    #     return final_doc


    def delete_transaction(self, transaction_id):
        """Removes a transaction (use only if necessary)."""
        return self.transactions.delete_one({"transactionID": transaction_id})
    

    def save_transaction_record(self,
                                tx_raw: Dict,
                                features: Optional[Dict] = None,
                                prediction: Optional[int] = None,
                                probability: Optional[float] = None,
                                user_id: Optional[int] = None):
        """
        Save a full transaction record including derived features and model output.

        - `tx_raw`: the original 8 raw fields provided by the frontend.
        - `features`: dictionary of derived features used by the model (keeps parity with training).
        - `prediction`: model label (0 or 1).
        - `probability`: model probability for the positive class (if available).
        - `user_id`: optional user identifier to link the record to a user account.

        This method is intentionally additive and does not change existing `process_transaction` behaviour.
        Call this from prediction endpoint after computing features and running the model.
        """
        tx_id = self._get_next_id("transactionid")

        # Create the base record
        record = {
            "transactionID": tx_id,
            "features": features or {},
            "isFraud": int(prediction) if prediction is not None else 0, # Match feature_engineering expectation
            "prediction": int(prediction) if prediction is not None else None,
            "probability": float(probability) if probability is not None else None,
            "user_id": user_id,
            "saved_at": datetime.utcnow()
        }
        
        # Unpack ALL raw fields into the top level of the record
        record.update(tx_raw)

        self.transactions.insert_one(record)
        return record


