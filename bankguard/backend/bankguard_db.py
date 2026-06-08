"""
Database Management module for BankGuard interactions via MongoDB.
"""
from pymongo import MongoClient, ReturnDocument
from datetime import datetime
from typing import Optional, Dict

class BankguardManager:
    def __init__(self, connection_string):
        self.client = MongoClient(connection_string)
        self.db = self.client.BankguardDB
        self.users = self.db.users
        self.transactions = self.db.transactions
        self.counters = self.db.counters

    def _get_next_id(self, counter_name):
        """Generates a sequential integer ID for relational tracking."""
        counter = self.counters.find_one_and_update(
            {"_id": counter_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return counter['seq']
    
    def add_user(self, name, email, password):
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
        return list(self.transactions.find({"initiator": user_id}).sort("transactionID", -1))
    
    def delete_transaction(self, transaction_id):
        return self.transactions.delete_one({"transactionID": transaction_id})
    
    def save_transaction_record(self, tx_raw: Dict, features: Optional[Dict] = None, prediction: Optional[int] = None, probability: Optional[float] = None, user_id: Optional[int] = None):
        """Archives the complete state of a transaction, including ML metrics, for auditing."""
        tx_id = self._get_next_id("transactionid")

        record = {
            "transactionID": tx_id,
            "features": features or {},
            "isFraud": int(prediction) if prediction is not None else 0,
            "probability": float(probability) if probability is not None else None,
            "saved_at": datetime.utcnow()
        }
        
        record.update(tx_raw)

        self.transactions.insert_one(record)
        return record