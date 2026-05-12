import os
import random
from dotenv import load_dotenv
from bankguard_db import BankguardManager

# Load environment variables
load_dotenv()
db_manager = BankguardManager(os.getenv("MONGO_URL"))

def reset_database():
    """Wipes the database clean to start fresh."""
    print("Clearing old data...")
    db_manager.users.delete_many({})
    db_manager.transactions.delete_many({})
    db_manager.counters.update_many({}, {"$set": {"seq": 0}})

def seed_data():
    """Generates realistic user history scaled for IDR (Indonesian Rupiah)."""
    print("Seeding new data...")
    
    # 1. Create two users
    initiator_id = db_manager.add_user("John Doe", "john@example.com", "password123")
    recipient_id = db_manager.add_user("Jane Doe", "jane@example.com", "password123")
    
    print(f"Created Initiator (ID: {initiator_id}) and Recipient (ID: {recipient_id})")

    # 2. Simulate 30 "Safe" Transactions to fill the 6, 12, and 24 windows
    # Starting balance: 25,000,000 IDR
    current_balance = 25000000.00
    
    for i in range(30):
        # John spends between Rp 150,000 and Rp 750,000 normally
        amount = round(random.uniform(150000.0, 750000.0), 2)
        new_balance = current_balance - amount
        
        safe_tx = {
            "transactionType": "PAYMENT",
            "amount": amount,
            "initiator": initiator_id,
            "recipient": recipient_id,
            "oldBalInitiator": current_balance,
            "newBalInitiator": new_balance,
            "oldBalRecipient": 0.0,
            "newBalRecipient": amount
        }
        
        # Save directly to DB (bypassing the ML model so it saves instantly)
        db_manager.save_transaction_record(
            tx_raw=safe_tx, 
            features={}, 
            prediction=0, # Mark as safe
            user_id=initiator_id
        )
        
        current_balance = new_balance

    print(f"Successfully generated 30 historical safe transactions for John.")
    print(f"John's current balance is: Rp {current_balance:,.2f}")
    print("\nDatabase is WARM and ready for testing!")

if __name__ == "__main__":
    print("WARNING: SEEDING THE DATABASE WILL CLEAR ITS CONTENTS!!")
    print("IF YOU WOULD LIKE TO CANCEL, SIMPLY PRESS \"ENTER\"")
    captcha = input("TYPE \"YES\" TO CONFIRM SEEDING: ")

    if captcha == "YES":
        # WARNING: This will delete everything in your DB!
        reset_database()
        seed_data()

    else: 
        print("\nYou have cancelled this operation")