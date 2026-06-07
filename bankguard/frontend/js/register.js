document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('registerForm');
    const statusDiv = document.getElementById('registerStatus');

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault(); 

        // Grab the values from the input fields
        const fullName = document.getElementById('fullName').value.trim();
        const email = document.getElementById('registerEmail').value.trim();
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('password_confirmation').value;
        
        // NEW: Grab the min and max transaction values
        const avgMin = parseFloat(document.getElementById('avgMinTransaction').value);
        const avgMax = parseFloat(document.getElementById('avgMaxTransaction').value);

        // Validation Logic
        if (!fullName || !email || !password || !confirmPassword || isNaN(avgMin) || isNaN(avgMax)) {
            statusDiv.style.color = "red";
            statusDiv.innerText = "All fields are required.";
            return;
        }

        if (avgMin >= avgMax) {
            statusDiv.style.color = "red";
            statusDiv.innerText = "Maximum transaction must be greater than minimum.";
            return;
        }

        if (password.length < 6) {
            statusDiv.style.color = "red";
            statusDiv.innerText = "Password must be at least 6 characters long.";
            return;
        }

        if (password !== confirmPassword) {
            statusDiv.style.color = "red";
            statusDiv.innerText = "Passwords do not match.";
            return;
        }

        statusDiv.style.color = "blue";
        statusDiv.innerText = "Creating secure account & generating history...";

        try {
            const response = await fetch('https://nevhs-bankguard-api.hf.space/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    fullName: fullName,
                    email: email,
                    password: password,
                    avgMinTransaction: avgMin, // NEW: Added to payload
                    avgMaxTransaction: avgMax  // NEW: Added to payload
                })
            });

            const data = await response.json();

            if (response.ok) {
                statusDiv.style.color = "green";
                statusDiv.innerText = `Success! Account created and seeded. User ID: ${data.userID}. Redirecting...`;
                
                setTimeout(() => {
                    window.location.href = "/html/index.html";
                }, 2000);
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