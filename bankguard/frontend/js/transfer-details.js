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

    const transactionForm = document.getElementById('transactionForm');
    const statusDiv = document.getElementById('formStatus');

    transactionForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Gather all form data
        // Note: We use parseFloat/parseInt because the Python model requires numbers, not strings
        const payload = {
            transactionType: document.getElementById('transactionType').value,
            amount: parseFloat(document.getElementById('amount').value),
            oldBalance: parseFloat(document.getElementById('oldBalance').value),
            newBalance: parseFloat(document.getElementById('newBalance').value)
        };

        statusDiv.style.color = "blue";
        statusDiv.innerText = "Analyzing transaction through BankGuard AI...";

        try {
            // Send data to the app
            const response = await fetch('http://127.0.0.1:5000/add_transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                // Save the ML model's prediction to localStorage
                localStorage.setItem('bg_isFraud', data.isFraud); // 0 or 1
                localStorage.setItem('bg_probability', data.probability || 0);
                localStorage.setItem('bg_txID', data.transactionID || 'Unknown');

                // Redirect to the combined results page
                window.location.href = "result.html";
            } else {
                statusDiv.style.color = "red";
                statusDiv.innerText = `Error: ${data.error}`;
            }
        } catch (error) {
            console.error("Fetch error:", error);
            statusDiv.style.color = "red";
            statusDiv.innerText = "Failed to connect to the server.";
        }
    });
});