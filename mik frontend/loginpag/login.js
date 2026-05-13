document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const username = document.getElementById("email").value;
        const password = document.getElementById("password").value;
        const loginBtn = document.querySelector(".login-btn");

        loginBtn.innerText = "Signing in...";
        loginBtn.disabled = true;

        try {
            const formData = new URLSearchParams();
            formData.append("username", username);
            formData.append("password", password);

            const response = await fetch("http://localhost:8000/auth/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: formData.toString()
            });

            if (!response.ok) {
                alert("Incorrect username or password");
                loginBtn.innerText = "Sign In";
                loginBtn.disabled = false;
                return;
            }

            const data = await response.json();
            localStorage.setItem("token", data.access_token);

            // Fetch user profile to get role
            const meResponse = await fetch("http://localhost:8000/auth/me", {
                headers: {
                    "Authorization": `Bearer ${data.access_token}`
                }
            });
            let meData;
            try {
                meData = await meResponse.json();
            } catch {
                alert("Could not read profile from server. Check that the API is running on port 8000.");
                loginBtn.innerText = "Sign In";
                loginBtn.disabled = false;
                return;
            }
            if (!meResponse.ok) {
                const msg =
                    typeof meData.detail === "string"
                        ? meData.detail
                        : meData.detail
                          ? JSON.stringify(meData.detail)
                          : "Profile request failed (" + meResponse.status + ")";
                alert("After login, profile load failed: " + msg);
                loginBtn.innerText = "Sign In";
                loginBtn.disabled = false;
                return;
            }

            // Redirect based on role
            const userRole = meData.role ? meData.role.toString().trim().toUpperCase() : "UNKNOWN";
            switch (userRole) {
                case "ADMIN":
                case "DIRECTOR":
                    window.location.href = "../Admin/Admin.html";
                    break;
                case "TEACHER":
                    window.location.href = "../teachpag/teach.html";
                    break;
                case "ACCOUNTANT":
                    window.location.href = "../financepag/finance.html";
                    break;
                case "PARENT":
                    // ensure parentpag exists or matches your actual directory name
                    window.location.href = "../parentpag/parent.html";
                    break;
                default:
                    alert("System unrecognized role: " + userRole);
                    loginBtn.innerText = "Sign In";
                    loginBtn.disabled = false;
            }
        } catch (error) {
            console.error("Login error", error);
            alert("Error connecting to server: " + error.message);
            loginBtn.innerText = "Sign In";
            loginBtn.disabled = false;
        }
    });
});
