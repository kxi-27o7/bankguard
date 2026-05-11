document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('registerForm');
    const statusDiv = document.getElementById('registerStatus');

    registerForm.addEventListener('submit', async (e) => {
        // Stop the page from reloading/redirecting immediately
        e.preventDefault(); 

        // Grab the values from the input fields
        const fullName = document.getElementById('fullName').value.trim();
        const email = document.getElementById('registerEmail').value.trim();
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('password_confirmation').value;

        // Validation Logic
        if (!fullName || !email || !password || !confirmPassword) {
            statusDiv.style.color = "red";
            statusDiv.innerText = "All fields are required.";
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

        // Display a loading message
        statusDiv.style.color = "blue";
        statusDiv.innerText = "Creating secure account...";

        // Send the data to the app
        try {
            const response = await fetch('http://127.0.0.1:5000/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    fullName: fullName,
                    email: email,
                    password: password // Note: at this moment, password is still plain text
                })
            });

            const data = await response.json();

            // Handle the backend response
            if (response.ok) {
                statusDiv.style.color = "green";
                statusDiv.innerText = `Success! Account has been created. Your User ID is: ${data.userID}. Redirecting to login...`;
                
                // Redirect to login page after 2 seconds
                setTimeout(() => {
                    window.location.href = "login.html";
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