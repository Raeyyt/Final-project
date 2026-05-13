const BASE_URL = "http://localhost:8000";

async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem("token");
    const headers = {
        "Content-Type": "application/json",
        ...options.headers
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${BASE_URL}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            // Unauthenticated, force logout (Unauthorized)
            localStorage.removeItem("token");
            window.location.href = "../loginpag/login.html";
            return null;
        }

        if (response.status === 204) return true;
        // No content error
        if (!response.ok) {
            try {
                return await response.json();
            } catch (jsonErr) {
                const text = await response.text();
                alert("CRITICAL BACKEND CRASH TEXT: " + text);
                return null;
            }
        }

        return await response.json();
    } catch (e) {
        alert("CRITICAL NETWORK CRASH: " + e.message);
        console.error("API error for " + endpoint, e);
        return null; // Handle silently for frontend UI error states
    }
}

function globalLogout() {
    localStorage.removeItem("token");
    window.location.href = "../loginpag/login.html";
}

function openSettingsModal() {
    let settingsModal = document.getElementById('globalSettingsModal');
    if (!settingsModal) {
        settingsModal = document.createElement('div');
        settingsModal.id = 'globalSettingsModal';
        settingsModal.style.cssText = 'display:flex; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); justify-content:center; align-items:center; z-index:9999;';
        settingsModal.innerHTML = `
            <div style="background:white; padding:30px; border-radius:12px; width:400px; color:#1e293b; box-shadow:0 10px 25px rgba(0,0,0,0.2);">
                <h3 style="margin-bottom:20px; text-align:center;">Change Credentials</h3>
                <form id="globalSettingsForm">
                    <label style="display:block; margin:10px 0 5px; font-weight:bold; font-size:14px;">Current Password (Required)</label>
                    <input type="password" id="setOldPass" required style="width:100%; padding:10px; margin-bottom:15px; border:1px solid #ddd; border-radius:5px;">
                    
                    <label style="display:block; margin:10px 0 5px; font-weight:bold; font-size:14px;">New Username (Optional)</label>
                    <input type="text" id="setNewUser" placeholder="Leave blank to keep current" style="width:100%; padding:10px; margin-bottom:15px; border:1px solid #ddd; border-radius:5px;">
                    
                    <label style="display:block; margin:10px 0 5px; font-weight:bold; font-size:14px;">New Password (Optional)</label>
                    <input type="password" id="setNewPass" placeholder="Leave blank to keep current" style="width:100%; padding:10px; margin-bottom:20px; border:1px solid #ddd; border-radius:5px;">
                    
                    <div style="display:flex; gap:10px;">
                        <button type="button" onclick="document.getElementById('globalSettingsModal').style.display='none'" style="flex:1; padding:12px; border:1px solid #ddd; background:white; border-radius:8px; cursor:pointer;">Cancel</button>
                        <button type="submit" style="flex:1; padding:12px; border:none; background:#2563eb; color:white; border-radius:8px; font-weight:bold; cursor:pointer;">Save Changes</button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(settingsModal);

        document.getElementById('globalSettingsForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.innerText = "Saving...";

            const oldPass = document.getElementById('setOldPass').value;
            const newUser = document.getElementById('setNewUser').value;
            const newPass = document.getElementById('setNewPass').value;

            const payload = { old_password: oldPass };
            if (newUser.trim() !== '') payload.username = newUser;
            if (newPass.trim() !== '') payload.new_password = newPass;

            const token = localStorage.getItem("token");
            const res = await fetch("http://localhost:8000/auth/me", {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token
                },
                body: JSON.stringify(payload)
            });

            btn.innerText = "Save Changes";
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem("token", data.access_token);
                alert("Credentials updated securely! Your new session has been activated.");
                document.getElementById('globalSettingsModal').style.display = 'none';
                e.target.reset();
            } else {
                const err = await res.json();
                alert("Update failed: " + (err.detail || "Invalid credentials"));
            }
        });
    } else {
        settingsModal.style.display = 'flex';
    }
}

function formatRoleLabel(role) {
    if (!role) return "User";
    const r = String(role).trim().toUpperCase();
    const labels = {
        ADMIN: "Administrator",
        DIRECTOR: "Director",
        TEACHER: "Teacher",
        ACCOUNTANT: "Accountant",
        PARENT: "Parent",
    };
    return labels[r] || r.charAt(0) + r.slice(1).toLowerCase();
}

function avatarUrlForUser(fullName, fallbackLabel) {
    const name = (fullName && String(fullName).trim()) || fallbackLabel || "User";
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=eff6ff&color=2563eb`;
}

/**
 * Fill header/profile UI from GET /auth/me.
 * roleEl: main label (role, e.g. "Director")
 * subtitleEl: secondary line (typically full name)
 * imgEl: optional avatar <img>
 */
async function hydrateCurrentUserHeader({ roleEl, subtitleEl, imgEl } = {}) {
    const me = await fetchAPI("/auth/me");
    if (!me) return null;
    const roleLabel = formatRoleLabel(me.role);
    const displayName = (me.full_name || me.username || "").trim();
    if (roleEl) roleEl.textContent = roleLabel;
    if (subtitleEl) subtitleEl.textContent = displayName || "Signed in";
    if (imgEl) {
        imgEl.src = avatarUrlForUser(displayName, roleLabel);
        imgEl.alt = displayName || roleLabel;
    }
    return me;
}
