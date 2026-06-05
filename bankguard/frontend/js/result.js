document.addEventListener('DOMContentLoaded', () => {
    // Profile dropdown
    const profileBtn = document.getElementById('profileBtn');
    const profileDropdown = document.getElementById('profileDropdown');
    const logoutBtn = document.getElementById('logoutBtn');

    profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        profileDropdown.classList.toggle('open');
    });

    document.addEventListener('click', () => {
        profileDropdown.classList.remove('open');
    });

    logoutBtn.addEventListener('click', () => {
        localStorage.clear();
        window.location.href = 'login.html';
    });
    // Read the data saved by transfer-details.js
    const isFraud = parseInt(localStorage.getItem('bg_isFraud')); // 0 or 1
    const rawProb = parseFloat(localStorage.getItem('bg_probability'));
    const txId = localStorage.getItem('bg_txID');

    // Format probability to a percentage (e.g., 0.88 -> 88)
    const probPercent = Math.round(rawProb * 100);
    const safePercent = 100 - probPercent;

    // Update Transaction IDs on the page
    document.querySelectorAll('.displayTxId').forEach(el => el.innerText = `TXN-${txId}`);

    // Update Probabilities on the page
    document.querySelectorAll('.displayProb').forEach(el => el.innerText = probPercent);
    document.querySelectorAll('.displayRisk').forEach(el => el.innerText = probPercent);
    document.querySelectorAll('.displaySafe').forEach(el => el.innerText = safePercent);

    // Grab our UI elements
    const body = document.getElementById('dynamicBody');
    const safeView = document.getElementById('safeView');
    const fraudView = document.getElementById('fraudView');

    // Update Transaction IDs on the page
    document.querySelectorAll('.displayTxId').forEach(el => el.innerText = `TXN-${txId}`);
    
    // Update Probabilities on the page
    document.querySelectorAll('.displayProb').forEach(el => {
        // If safe, we want "confidence in safety" (100 - fraud prob). If fraud, we want the fraud prob.
        el.innerText = isFraud === 1 ? probPercent : (100 - probPercent); 
    });

    // Switch the UI based on the AI Prediction
    if (isFraud === 1) {
        body.className = "fraud-theme"; // Applies your red CSS styles
        fraudView.style.display = "block";
    } else {
        body.className = "safe-theme"; // Applies your green/blue CSS styles
        safeView.style.display = "block";
    }
});