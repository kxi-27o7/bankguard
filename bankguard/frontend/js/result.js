document.addEventListener('DOMContentLoaded', () => {
    // Profile dropdown logic
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
    const isFraud = parseInt(localStorage.getItem('bg_isFraud')); 
    const rawProb = parseFloat(localStorage.getItem('bg_probability'));
    const txId = localStorage.getItem('bg_txID');

    const probPercent = Math.round(rawProb * 100);
    const safePercent = 100 - probPercent;

    // Grab our UI elements
    const body = document.getElementById('dynamicBody');
    const safeView = document.getElementById('safeView');
    const fraudView = document.getElementById('fraudView');

    // Update Transaction IDs
    document.querySelectorAll('.displayTxId').forEach(el => el.innerText = `TXN-${txId}`);
    
    // Update Risk and Safe Specific Metrics
    document.querySelectorAll('.displayRisk').forEach(el => el.innerText = probPercent);
    document.querySelectorAll('.displaySafe').forEach(el => el.innerText = safePercent);

    // Dynamic Probability Display based on outcome
    document.querySelectorAll('.displayProb').forEach(el => {
        el.innerText = isFraud === 1 ? probPercent : safePercent; 
    });

    // Switch the UI based on the AI Prediction
    if (isFraud === 1) {
        body.className = "fraud-theme"; 
        fraudView.style.display = "block";
    } else {
        body.className = "safe-theme"; 
        safeView.style.display = "block";
    }
});