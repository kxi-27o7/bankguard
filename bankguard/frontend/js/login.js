document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const statusDiv = document.getElementById('loginStatus');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault(); 

        const email = document.getElementById('loginEmail').value.trim();
        const password = document.getElementById('loginPassword').value;

        if (!email || !password) {
            statusDiv.style.color = "red";
            statusDiv.innerText = "Please enter both email and password.";
            return;
        }

        statusDiv.style.color = "blue";
        statusDiv.innerText = "Authenticating...";

        try {
            const response = await fetch('https://nevhs-bankguard-api.hf.space/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, password: password })
            });

            const data = await response.json();

            if (response.ok) {
                statusDiv.style.color = "green";
                statusDiv.innerText = `Welcome back, ${data.name}! Redirecting...`;
                
                // FIXED: Keys now match what transfer-details.js expects
                localStorage.setItem('userID', data.userID);
                localStorage.setItem('userName', data.name);

                setTimeout(() => {
                    window.location.href = "html/transfer-details.html";
                }, 1500);
            } else {
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