# Changelog

## Frontend Dynamic Integration

* **Added Global API Helper (`mik frontend/api.js`)**: Centralized `fetch()` logic to automatically attach the JWT access token from `localStorage` into the headers of all backend requests, and automatically redirect unauthorized sessions back to login.
* **Updated Login Form (`mik frontend/loginpag/login.html`)**: Added the `loginForm` ID and imported `login.js`.
* **Created Login Flow Script (`mik frontend/loginpag/login.js`)**: Listens to the submit event, authenticates with FastAPI, stores the JWT securely to browser storage, fetches the user's role, and routes the directory path to the appropriate dashboard template.
* **Wired Teacher Dashboard (`teachpag/teach.js`)**: Now uses `fetchAPI("/students/")` to pull students assigned dynamically, replacing mock arrays. Posting attendance directly executes `POST /attendance`.
* **Wired Parent Portal (`parentpag/parent.js`)**: Pulls real payment status and due dates from `GET /payments/` scoped safely to their child's records via previously authored backend limits.
* **Refined Modals & Settings Engine (`mik frontend/api.js`)**: Extended cross-dashboard utility appending dynamic `Settings` modals mapped successfully to `PATCH /auth/me`.
* **Elevated Director Privileges (`backend/app/routers/classes.py` & `backend/app/routers/students.py`)**: Secured `POST`, `PATCH`, and `DELETE` access levels accommodating native modifications scaling vertically.
* **Injected Classroom Assignments UI (`mik frontend/Admin/Admin.js`)**: Developed dynamic layout enforcing 1-to-1 assignments rendering backend database limits natively without crashes.
* **Expanded Student Roster Hub (`mik frontend/Admin/Admin.js`)**: Attached seamless student creations inherently locking newly admitted records to the target classroom's assigned instructor automatically.
* **Updated Forms (`mik frontend/Admin/Admin.js` & `mik frontend/parentpag/parent.js`)**: Connected Add User bounds to dynamically minted mock emails generating hashed `bcrypt` variables upon commit, and bound dummy gateway interactions safely triggering structured `PATCH` calls handling monetary increments accurately in sync seamlessly.
