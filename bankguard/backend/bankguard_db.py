from pymongo import MongoClient, ReturnDocument

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

    def process_transaction(self, tx_data, model=None):
        """
        Logic: Checks history -> Predicts Fraud -> Saves to DB
        tx_data should contain: initiator, recipient, amount, transactionType
        """
        initiator_id = tx_data['initiator']
        
        # 1. Check for previous transactions from the getter
        history = self.get_user_history(initiator_id)
        
        # 2. Assume not fraud if it's the first transaction
        # NOTE: Might be changed accordingly
        if not history:
            is_fraud_prediction = False
            old_balance = 1000.00 # Standard starting mockup balance (change if necessary)

        else:
            # Get the most recent balance from the latest transaction
            old_balance = history[0]['newBalInitiator']
            
            # 3. Machine Learning Prediction
            if model:
                # Prepare features for your Random Forest (Example format)
                features = [[tx_data['amount'], old_balance, len(history)]]
                is_fraud_prediction = bool(model.predict(features)[0])

            else:
                is_fraud_prediction = False # Fallback if model isn't loaded

        # 4. Final Document Construction
        tx_id = self._get_next_id("transactionid")
        final_doc = {
            "transactionID": tx_id,
            "transactionType": tx_data['transactionType'],
            "amount": tx_data['amount'],
            "initiator": initiator_id,
            "oldBalInitiator": old_balance,
            "newBalInitiator": old_balance - tx_data['amount'],
            "recipient": tx_data['recipient'],
            "oldBalRecipient": 0.0, # Simplified for mockup (Change if necessary)
            "newBalRecipient": tx_data['amount'],
            "isFraud": is_fraud_prediction
        }
        
        self.transactions.insert_one(final_doc)
        return final_doc


    def delete_transaction(self, transaction_id):
        """Removes a transaction (use only if necessary)."""
        return self.transactions.delete_one({"transactionID": transaction_id})
    


