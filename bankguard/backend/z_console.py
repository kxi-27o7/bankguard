import os
import sys
import random
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Suppress noisy scikit-learn/pandas warnings for a clean console
warnings.filterwarnings("ignore", category=UserWarning)

# Local backend modules
from bankguard_db import BankguardManager
from feature_engineering import make_features
from model_utils import load_model, predict

# ---------------------------------------------------------
# 1. Initialization
# ---------------------------------------------------------
load_dotenv()
db_manager = BankguardManager(os.getenv("MONGO_URL"))

# Global State for Target User
current_user_id = 1

# Load Model
BASE_DIR = Path(__file__).resolve().parent.parent 
MODEL_PATH = BASE_DIR / 'ml' / 'model' / 'model.pkl'
if not MODEL_PATH.exists():
    MODEL_PATH = BASE_DIR / 'ml' / 'model' / 'model.joblib'

try:
    if os.path.exists(MODEL_PATH):
        MODEL = load_model(MODEL_PATH)
        print("✅ Machine Learning Model Loaded Successfully.")
    else:
        MODEL = None
        print("⚠️ Warning: Model file not found. Predictions will fail.")
except Exception as e:
    MODEL = None
    print(f"❌ Error loading model: {e}")

# ---------------------------------------------------------
# 2. Database Seeding Logic
# ---------------------------------------------------------
def reset_database():
    print("\n[SYSTEM] Clearing old data...")
    db_manager.users.delete_many({})
    db_manager.transactions.delete_many({})
    db_manager.counters.update_many({}, {"$set": {"seq": 0}})
    print("[SYSTEM] Database wiped clean.")

def seed_data():
    global current_user_id
    print("\n[SYSTEM] Seeding warm-up data...")
    
    # Auto-target the newly created user
    current_user_id = db_manager.add_user("John Doe", "john@example.com", "password123")
    
    current_balance = 50000000.00 
    
    for i in range(30):
        # Normal safe spending is between 150k and 750k IDR
        amount = round(random.uniform(150000.0, 750000.0), 2)
        new_balance = current_balance - amount
        
        safe_tx = {
            "initiator": current_user_id,
            "transactionType": "PAYMENT",
            "amount": amount,
            "oldBalance": current_balance,
            "newBalance": new_balance
        }
        
        db_manager.save_transaction_record(tx_raw=safe_tx, features={}, prediction=0, probability=0.0)
        current_balance = new_balance

    print(f"[SYSTEM] Generated 30 safe historical transactions for John (ID: {current_user_id}).")
    print(f"[SYSTEM] Starting balance is now: Rp {current_balance:,.2f}")

# ---------------------------------------------------------
# 3. Live Model Simulation Logic
# ---------------------------------------------------------
def run_live_transaction(user_id, is_fraud_attempt=False):
    if not MODEL:
        print("\n[ERROR] Cannot simulate. Model is not loaded.")
        return

    # 1. Fetch current history to get the latest balance
    history = list(reversed(db_manager.get_user_history(user_id)))
    
    if not history:
        print(f"\n[ERROR] No history found for User ID {user_id}. Please seed the database or choose an active user.")
        return
        
    current_balance = history[-1].get('newBalance', 0.0)

    # 2. Generate a transaction amount based on the scenario
    if is_fraud_attempt:
        # Fraud: Draining 100% of the account
        amount = current_balance
        tx_type = "TRANSFER"
        print(f"\n[SIMULATION] Initiating FRAUDULENT transaction: Draining Rp {amount:,.2f}...")
    else:
        # Safe: Normal daily spending pattern
        amount = round(random.uniform(150000.0, 750000.0), 2)
        tx_type = "PAYMENT"
        print(f"\n[SIMULATION] Initiating SAFE transaction: Spending Rp {amount:,.2f}...")

    new_balance = current_balance - amount

    # 3. Create the standard 5-field payload
    tx_raw = {
        "initiator": user_id,
        "transactionType": tx_type,
        "amount": amount,
        "oldBalance": current_balance,
        "newBalance": new_balance
    }

    # 4. Feature Engineering
    features = make_features(tx_raw, history={'initiator': history})

    # 5. Model Prediction
    label, probability = predict(MODEL, features, threshold=0.5)

    # 6. Save to Database
    db_manager.save_transaction_record(
        tx_raw=tx_raw, 
        features=features, 
        prediction=label, 
        probability=probability
    )

    # Output Results
    print("-" * 40)
    print(f"Outcome      : {'🚨 FRAUD DETECTED' if label == 1 else '✅ SAFE'}")
    print(f"Probability  : {probability * 100:.2f}% risk")
    print(f"Amount       : Rp {amount:,.2f}")
    print(f"New Balance  : Rp {new_balance:,.2f}")
    print("-" * 40)

# ---------------------------------------------------------
# 4. Batch Simulation Logic
# ---------------------------------------------------------
def run_batch_simulations(user_id):
    if not MODEL:
        print("\n[ERROR] Cannot simulate. Model is not loaded.")
        return

    try:
        num_sims = int(input("\nHow many transactions would you like to simulate? (e.g., 100): "))
    except ValueError:
        print("Invalid number. Returning to main menu.")
        return

    print(f"\n[SYSTEM] Running {num_sims} simulations for User ID {user_id}. Please wait...")

    # Tracking metrics for Confusion Matrix
    TP = 0  # True Positive: Actual Fraud, Predicted Fraud
    TN = 0  # True Negative: Actual Safe, Predicted Safe
    FP = 0  # False Positive: Actual Safe, Predicted Fraud
    FN = 0  # False Negative: Actual Fraud, Predicted Safe

    for i in range(num_sims):
        # --- Progress Bar Logic ---
        progress = (i + 1) / num_sims
        bar_length = 40
        block = int(round(bar_length * progress))
        text = f"\rProgress: [{'█' * block + '-' * (bar_length - block)}] {progress * 100:.1f}% ({i+1}/{num_sims})"
        sys.stdout.write(text)
        sys.stdout.flush()

        # 1. Fetch current history to keep balances accurate
        history = list(reversed(db_manager.get_user_history(user_id)))
        current_balance = history[-1].get('newBalance', 0.0) if history else 50000000.0

        # Safety net: If the account was drained by a previous "fraud" test, deposit 50 Million more
        if current_balance < 2000000.0:
            current_balance += 50000000.0
            deposit_tx = {
                "initiator": user_id, "transactionType": "DEPOSIT", "amount": 50000000.0, 
                "oldBalance": current_balance - 50000000.0, "newBalance": current_balance
            }
            db_manager.save_transaction_record(tx_raw=deposit_tx, features={}, prediction=0, probability=0.0)

        # 2. Determine scenario (Randomly assign 15% of transactions as Fraud)
        is_actual_fraud = random.random() < 0.15

        if is_actual_fraud:
            # FIXED FRAUD BEHAVIOR: Exactly 100% of the account is drained
            amount = current_balance 
            tx_type = "TRANSFER"
        else:
            # Safe: Normal spending habits
            amount = round(random.uniform(150000.0, 750000.0), 2)
            tx_type = "PAYMENT"

        new_balance = current_balance - amount

        # 3. Create Payload
        tx_raw = {
            "initiator": user_id,
            "transactionType": tx_type,
            "amount": amount,
            "oldBalance": current_balance,
            "newBalance": new_balance
        }

        # 4. Feature Engineering & Prediction
        features = make_features(tx_raw, history={'initiator': history})
        label, probability = predict(MODEL, features, threshold=0.5)

        # 5. Tally confusion matrix metrics
        if is_actual_fraud and label == 1:
            TP += 1
        elif not is_actual_fraud and label == 0:
            TN += 1
        elif not is_actual_fraud and label == 1:
            FP += 1
        elif is_actual_fraud and label == 0:
            FN += 1

        # 6. Save to DB
        db_manager.save_transaction_record(
            tx_raw=tx_raw, 
            features=features, 
            prediction=label, 
            probability=probability
        )

    # Print newline after progress bar completes
    print("\n")

    # 7. Calculate Advanced Metrics
    total_actual_fraud = TP + FN
    total_actual_safe = TN + FP
    
    accuracy = (TP + TN) / num_sims if num_sims > 0 else 0
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # 8. Print Output Statistics
    print("="*60)
    print("📊 BATCH SIMULATION ADVANCED RESULTS")
    print("="*60)
    print(f"Total Transactions Simulated : {num_sims}")
    print(f"Actual Fraud Generated       : {total_actual_fraud}")
    print(f"Actual Safe Generated        : {total_actual_safe}")
    print("-" * 60)
    print("📌 CONFUSION MATRIX:")
    print(f"                     Predicted FRAUD   Predicted SAFE")
    print(f"Actual FRAUD      |  TP: {TP:<11} |  FN: {FN:<11} |")
    print(f"Actual SAFE       |  FP: {FP:<11} |  TN: {TN:<11} |")
    print("-" * 60)
    print("📈 MODEL PERFORMANCE METRICS:")
    print(f"Accuracy  : {accuracy * 100:>6.2f}%  (Overall correctness)")
    print(f"Precision : {precision * 100:>6.2f}%  (When it flags fraud, how often is it right?)")
    print(f"Recall    : {recall * 100:>6.2f}%  (How much actual fraud did it catch?)")
    print(f"F1-Score  : {f1_score * 100:>6.2f}%  (Balance of Precision and Recall)")
    print("="*60)

# ---------------------------------------------------------
# 5. Stress Testing Logic
# ---------------------------------------------------------
def run_amount_stress_test(user_id):
    print(f"\n[SYSTEM] Running Amount Sensitivity Stress Test for User ID: {user_id}")
    if not MODEL:
        print("[ERROR] Cannot simulate. Model is not loaded.")
        return

    # 1. Fetch history once to act as a consistent baseline for all predictions
    history = list(reversed(db_manager.get_user_history(user_id)))
    if not history:
        print(f"[ERROR] No history found for User ID {user_id}. Please seed data first.")
        return

    # 2. Use a massive static starting balance so we ONLY test the amount's impact, 
    # not the model reacting to a drained bank account.
    static_old_balance = 50000000.00 

    print("Scanning amounts from Rp 10,000 to Rp 1,000,000 (Step: Rp 10,000)...\n")

    # State tracking variables
    current_state = None
    start_range_amount = 10000
    results = []

    # 3. The Sweep Loop
    for amount in range(10000, 1000000 + 1, 10000):
        # Create payload
        tx_raw = {
            "initiator": user_id,
            "transactionType": "PAYMENT",
            "amount": float(amount),
            "oldBalance": static_old_balance,
            "newBalance": static_old_balance - float(amount)
        }

        # Engineer features & Predict (Using standard 50% threshold)
        features = make_features(tx_raw, history={'initiator': history})
        label, prob = predict(MODEL, features, threshold=0.50)

        # 4. Anomaly Detection (Recording when the prediction flips)
        if current_state is None:
            # First run setup
            current_state = label
            start_range_amount = amount
            
        elif label != current_state:
            # The model flipped its prediction! Record the previous block.
            state_str = "🚨 FRAUD" if current_state == 1 else "✅ SAFE "
            end_amount = amount - 10000
            results.append(f"{state_str} | Rp {start_range_amount:>10,.2f}  ->  Rp {end_amount:>10,.2f}")
            
            # Start tracking the new block
            current_state = label
            start_range_amount = amount

    # Record the final block after the loop finishes
    if current_state is not None:
        state_str = "🚨 FRAUD" if current_state == 1 else "✅ SAFE "
        results.append(f"{state_str} | Rp {start_range_amount:>10,.2f}  ->  Rp 1,000,000.00")

    # 5. Output the simplified map
    print("="*60)
    print("📊 SENSITIVITY TEST RESULTS (BOUNDARY MAP)")
    print("="*60)
    for res in results:
        print(res)
    print("="*60)

# ---------------------------------------------------------
# 6. Interactive Menu
# ---------------------------------------------------------
def main_menu():
    global current_user_id
    
    while True:
        print(f"\n=== BankGuard Testing Console (Target ID: {current_user_id}) ===")
        print("1. Change Target User ID")
        print("2. Wipe Database & Seed Warm Data")
        print("3. Simulate: Normal Transaction (Safe)")
        print("4. Simulate: Anomalous Transaction (Fraud)")
        print("5. Simulate: Batch Multi-Transaction Run")
        print("6. Simulate: Amount Sensitivity Stress Test")
        print("7. Exit")
        
        choice = input("Select an option (1-7): ")

        if choice == '1':
            try:
                new_id = int(input("\nEnter the User ID you want to target: "))
                user = db_manager.users.find_one({'userID': new_id})
                
                if user:
                    current_user_id = new_id
                    print(f"[SUCCESS] Target switched to User ID: {current_user_id} ({user.get('name', 'Unknown')})")
                else:
                    print(f"[ERROR] No user found with ID {new_id} in the database. Keeping target as {current_user_id}.")
            except ValueError:
                print("[ERROR] Invalid input. Please enter a valid numerical ID.")
                
        elif choice == '2':
            confirm = input("WARNING: This wipes the database. Type YES to confirm: ")
            if confirm == "YES":
                reset_database()
                seed_data()
            else:
                print("Cancelled.")
                
        elif choice == '3':
            run_live_transaction(current_user_id, is_fraud_attempt=False)
            
        elif choice == '4':
            run_live_transaction(current_user_id, is_fraud_attempt=True)
            
        elif choice == '5':
            run_batch_simulations(current_user_id)
            
        elif choice == '6':
            run_amount_stress_test(current_user_id)
                
        elif choice == '7':
            print("Exiting console...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()