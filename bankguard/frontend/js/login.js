document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const statusDiv = document.getElementById('loginStatus');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Stop default form submission

        // Grab values
        const email = document.getElementById('loginEmail').value.trim();
        const password = document.getElementById('loginPassword').value;

        // Basic frontend validation
        if (!email || !password) {
            statusDiv.style.color = "red";
            statusDiv.innerText = "Please enter both email and password.";
            return;
        }

        statusDiv.style.color = "blue";
        statusDiv.innerText = "Authenticating...";

        try {
            const response = await fetch('http://127.0.0.1:5000/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok) {
                statusDiv.style.color = "green";
                statusDiv.innerText = `Welcome back, ${data.name}! Redirecting...`;
                
                // CRITICAL: Save the userID to localStorage so the transfer page knows who is logged in
                localStorage.setItem('bankguard_userID', data.userID);
                localStorage.setItem('bankguard_userName', data.name);

                // Redirect after 1.5 seconds
                setTimeout(() => {
                    window.location.href = "transfer-details.html";
                }, 1500);
            } else {
                // Display the specific error message from the backend (e.g., "Incorrect password")
                statusDiv.style.color = "red";
                statusDiv.innerText = data.error;
            }
        } catch (error) {
            console.error("Login fetch error:", error);
            statusDiv.style.color = "red";
            statusDiv.innerText = "Failed to connect to the server.";
        }
    });
});