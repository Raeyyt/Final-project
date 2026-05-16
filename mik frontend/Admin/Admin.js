// Function to switch between "Pages"
async function showPage(pageName) {
    const content = document.getElementById('dynamic-content');

    if (window.adminAttendanceChartInstance) {
        try {
            window.adminAttendanceChartInstance.destroy();
        } catch (e) {
            /* chart node may already be gone */
        }
        window.adminAttendanceChartInstance = null;
    }

    // Update active class in sidebar
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    const activeLi = document.querySelector(`.nav-links li[onclick="showPage('${pageName}')"]`);
    if (activeLi) {
        activeLi.classList.add('active');
    }

    // Ensure auth before loading dashboard content
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../loginpag/login.html";
        return;
    }

    if (!content) {
        console.error("Admin: #dynamic-content not found");
        return;
    }

    content.innerHTML = `<div style="padding:32px;color:#64748b;display:flex;align-items:center;gap:12px;font-size:15px;"><i class='bx bx-loader-alt bx-spin' style="font-size:22px;color:#2563eb"></i><span>Loading…</span></div>`;

    if (pageName === 'dashboard') {
        const [stats, classMetrics] = await Promise.all([
            fetchAPI("/dashboard/stats"),
            fetchAPI("/dashboard/class-metrics")
        ]);
        const statsErr =
            !stats ||
            (typeof stats === "object" && stats !== null && Object.prototype.hasOwnProperty.call(stats, "detail"));
        if (statsErr) {
            const detail =
                stats && typeof stats.detail === "string"
                    ? stats.detail
                    : stats && stats.detail
                      ? JSON.stringify(stats.detail)
                      : "No data (check that the backend is running and you are signed in as Admin or Director).";
            content.innerHTML = `
                <div style="max-width:560px;margin:40px auto;padding:24px;background:#fff;border-radius:12px;border:1px solid #fecaca;color:#991b1b;">
                    <h2 style="margin:0 0 12px 0;font-size:1.1rem;">Dashboard could not load</h2>
                    <p style="margin:0;line-height:1.5;color:#7f1d1d;">${String(detail).replace(/</g, "&lt;")}</p>
                    <p style="margin:16px 0 0 0;font-size:14px;color:#64748b;">If you just logged in, confirm Docker/Postgres is up and the <strong>Backend</strong> window shows no errors, then refresh this page.</p>
                </div>`;
            return;
        }

        const metricsList = Array.isArray(classMetrics) ? classMetrics : [];
        window.currentAdminMetrics = metricsList;

        let classBarsHTML = metricsList.length > 0 ? metricsList.map(m => {
            const totalRec = m.present_today + m.absent_today;
            const presPct = totalRec === 0 ? 0 : Math.round((m.present_today / totalRec) * 100);
            const absPct = totalRec === 0 ? 0 : Math.round((m.absent_today / totalRec) * 100);
            
            return `
            <div style="margin-bottom: 20px;">
                <h4 style="margin-bottom: 8px; color: #1e293b; font-size:14px; display:flex; justify-content:space-between;">
                    ${m.class_name} 
                    <span style="font-size: 12px; color: #64748b; font-weight: normal;">${m.total_students} Enrolled</span>
                </h4>
                <div style="display:flex; height:18px; background:#e2e8f0; border-radius:6px; overflow:hidden;">
                    <div style="width: ${presPct}%; background: #0284c7; transition: width 1s;" title="Present: ${m.present_today}"></div>
                    <div style="width: ${absPct}%; background: #ef4444; transition: width 1s;" title="Absent: ${m.absent_today}"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-top:5px; color:#64748b; font-weight:bold;">
                    <span style="color:#0369a1"><i class='bx bxs-user-check'></i> Present: ${m.present_today} (${presPct}%)</span>
                    <span style="color:#ef4444"><i class='bx bxs-user-x'></i> Absent: ${m.absent_today} (${absPct}%)</span>
                </div>
            </div>`;
        }).join('') : `<p style="color:#64748b">No active class telemetry available.</p>`;

        content.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card"><span>Total Students</span><h1>${stats.total_students}</h1></div>
                <div class="stat-card"><span>Total Classes</span><h1>${stats.total_classes}</h1></div>
                <div class="stat-card"><span>Attendance Today</span><h1>${stats.attendance_today}</h1></div>
            </div>
            
            <div class="dashboard-layout" style="display:grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 20px;">
                <div class="summary-box" style="padding: 24px; background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
                    <h3 style="margin-bottom: 20px; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px; color:#1e293b; display:flex; justify-content:space-between; align-items:center;">
                        <span><i class='bx bx-line-chart' style="color:#2563eb"></i> Live Classroom Analytics</span>
                        <button onclick="exportAdminCSV()" style="font-size:12px; padding:6px 12px; background:#2563eb; color:white; border:none; border-radius:4px; cursor:pointer; display:flex; align-items:center; gap:5px;"><i class='bx bx-export'></i> Export</button>
                    </h3>
                    ${classBarsHTML}
                </div>
                
                <div class="actions-box" style="padding: 24px; background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); height: fit-content;">
                    <h3 style="margin-bottom: 15px; color:#1e293b;">Financial Alerts</h3>
                    <p style="margin-top: 10px; font-size:14px; background:#fff7ed; padding:12px; border-radius:8px; border-left:4px solid #f59e0b;">
                        Pending Fee Approvals: <strong style="color:#b45309">${stats.payments_pending}</strong>
                    </p>
                    <p style="margin-top: 10px; font-size:14px; background:#fef2f2; padding:12px; border-radius:8px; border-left:4px solid #ef4444;">
                        Overdue Payments: <strong style="color:#b91c1c">${stats.payments_overdue}</strong>
                    </p>
                    
                    ${window._adminPortalRole === 'ADMIN' ? `
                    <h3 style="margin-top: 30px; margin-bottom: 15px; color:#1e293b;">Quick Actions</h3>
                    <button class="btn-add" style="margin-top:10px; background:#ef4444; width:100%;" onclick="resetQuarter()"><i class='bx bx-reset'></i> Reset Quarter</button>
                    ` : ''}
                </div>
            </div>
        `;
        
        window.resetQuarter = async () => {
            if (confirm("WARNING: Are you absolutely sure you want to reset the system for a new quarter?\n\nThis will permanently delete ALL attendance records and ALL master schedules. Payments will NOT be deleted. This action CANNOT be undone.")) {
                try {
                    const res = await fetchAPI("/dashboard/reset-quarter", { method: 'POST' });
                    if (res && res.message) {
                        alert(res.message);
                        window.location.reload();
                    }
                } catch(e) {
                    alert("Failed to reset the quarter.");
                }
            }
        };
    } else if (pageName === 'users') {
        const users = await fetchAPI("/auth/users");
        
        let htmlBlock = `<div style="display:flex; justify-content:space-between; align-items:center;">
            <h2 style="margin:0;">User Management</h2>
            <button class="btn-add" style="background:#64748b; width:auto; padding:8px 16px;" onclick="openUserModal()">Add User</button>
        </div>`;
        
        if (users && users.length > 0) {
            const roles = ["ADMIN", "DIRECTOR", "TEACHER", "ACCOUNTANT", "PARENT"];
            roles.forEach(role => {
                const roleUsers = users.filter(u => u.role === role);
                if (roleUsers.length > 0) {
                    htmlBlock += `<h3 style="margin-top: 30px; margin-bottom: 10px; color: #1e293b; padding-left: 5px;">${role}s</h3>`;
                    htmlBlock += `<div style="background:white; padding:20px; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.05);">`;
                    htmlBlock += `<table style="width:100%; border-collapse:collapse; text-align:left;">`;
                    htmlBlock += `<tr style="border-bottom:1px solid #e2e8f0;">
                        <th style="padding:15px 10px; color:#475569; width:40%;">Name</th>
                        <th style="color:#475569; width:30%;">Username</th>
                        <th style="color:#475569; text-align:right;">Action</th>
                    </tr>`;
                    
                    roleUsers.forEach(u => {
                        const titleExtra = role === 'TEACHER' && u.teaching_title
                            ? `<div style="font-size:12px;color:#64748b;font-weight:500;">Subject: ${u.teaching_title}</div>`
                            : '';
                        htmlBlock += `<tr style="border-bottom:1px solid #f8fafc;">
                            <td style="padding:15px 10px; font-weight:600; color:#1e293b;">${u.full_name}${titleExtra}</td>
                            <td style="color:#64748b;">${u.username}</td>
                            <td style="text-align:right;">
                                <button onclick="deleteUser(${u.id})" style="background:#ef4444; color:white; padding:6px 12px; font-weight:600; border:none; border-radius:6px; cursor:pointer; transition: 0.2s;">Remove</button>
                            </td>
                        </tr>`;
                    });
                    htmlBlock += `</table></div>`;
                }
            });
        } else {
            htmlBlock += `<p style="padding: 20px; color: #64748b;">No users found natively.</p>`;
        }
        
        content.innerHTML = htmlBlock;
        
        window.deleteUser = async (userId) => {
            if (!confirm("Are you sure you want to permanently remove this user? Their assigned students/classes will be unlinked automatically.")) return;
            const res = await fetchAPI(`/auth/users/${userId}`, { method: "DELETE" });
            alert("User definitively removed.");
            showPage('users');
        };
    } else if (pageName === 'classes') {
        const classes = await fetchAPI("/classes/");
        const teachers = await fetchAPI("/teachers/");

        let htmlBlock = `<h2>Classrooms & Teacher Assignments</h2>`;
        htmlBlock += `<div style="background:white; padding:20px; border-radius:8px; margin-top:20px; box-shadow:0 2px 10px rgba(0,0,0,0.05);">`;
        
        htmlBlock += `<div style="margin-bottom:20px; display:flex; gap:10px;">
            <input type="text" id="newClassName" placeholder="Class Name (e.g. Grade 10-A)" style="padding:8px; border:1px solid #cbd5e1; border-radius:6px; flex:1;">
            <button onclick="createClass()" style="background:#2563eb; color:white; padding:8px 16px; font-weight:bold; border:none; border-radius:6px; cursor:pointer;">Add Class</button>
        </div>`;
        
        htmlBlock += `<table style="width:100%; border-collapse:collapse; text-align:left;">`;
        htmlBlock += `<tr style="border-bottom:1px solid #e2e8f0;"><th style="padding:15px 10px; color:#475569;">Class Name</th><th style="color:#475569;">Assigned Teacher</th><th style="color:#475569;">Action</th></tr>`;

        const assignedTeacherIds = new Set(classes ? classes.map(c => c.teacher_id).filter(id => id !== null) : []);
        if (classes && classes.length > 0) {
            classes.forEach(c => {
                htmlBlock += `<tr style="border-bottom:1px solid #f8fafc;">
                    <td style="padding:15px 10px; font-weight:600; color:#1e293b;">${c.name}</td>
                    <td>
                        <select id="teacherSelect_${c.id}" style="padding:8px 12px; border-radius:6px; border:1px solid #cbd5e1; width:220px; outline:none;">
                            <option value="">-- Unassigned --</option>
                            ${teachers && teachers.length > 0 ? teachers.filter(t => !assignedTeacherIds.has(t.id) || c.teacher_id === t.id).map(t => `<option value="${t.id}" ${c.teacher_id === t.id ? 'selected' : ''}>${t.full_name}${t.teaching_title ? ' — ' + t.teaching_title : ''}</option>`).join('') : ''}
                        </select>
                    </td>
                    <td>
                        <button onclick="assignTeacher(${c.id})" style="background:#2563eb; color:white; padding:8px 16px; font-weight:600; border:none; border-radius:6px; cursor:pointer; transition:0.2s; margin-right:5px;">Secure Assign</button>
                        <button onclick="deleteClass(${c.id})" style="background:#ef4444; color:white; padding:8px 12px; font-weight:600; border:none; border-radius:6px; cursor:pointer;">Delete</button>
                    </td>
                </tr>`;
            });
        } else {
            htmlBlock += `<tr><td colspan="3" style="padding:20px; text-align:center;">No classrooms found natively.</td></tr>`;
        }

        htmlBlock += `</table></div>`;
        content.innerHTML = htmlBlock;
        
        window.createClass = async () => {
            const name = document.getElementById('newClassName').value;
            if (!name) return alert("Class name required");
            const res = await fetchAPI("/classes/", { method: "POST", body: JSON.stringify({ name: name }) });
            if (res) showPage('classes');
            else alert("Failed to create class. Name might already exist.");
        };

        window.deleteClass = async (classId) => {
            if (!confirm("Are you sure you want to delete this class? User assignments might be affected.")) return;
            const res = await fetchAPI(`/classes/${classId}`, { method: "DELETE" });
            if (res) alert("Class removed securely from database layers.");
            showPage('classes');
        };

        window.assignTeacher = async (classId) => {
            const teacherIdVal = document.getElementById(`teacherSelect_${classId}`).value;
            const payload = teacherIdVal ? { teacher_id: parseInt(teacherIdVal) } : { teacher_id: null };

            const btn = event.target;
            const originalText = btn.innerText;
            btn.innerText = "Applying...";
            btn.disabled = true;

            const res = await fetchAPI(`/classes/${classId}`, {
                method: "PATCH",
                body: JSON.stringify(payload)
            });

            btn.innerText = originalText;
            btn.disabled = false;

            if (res) {
                alert("Database accepted: Classroom updated securely!");
                showPage('classes');
            } else {
                alert("Security Gateway: Failed to assign teacher. The teacher is already rigorously assigned to supervise a distinct classroom.");
            }
        };

    } else if (pageName === 'schedules') {
        const classes = await fetchAPI("/classes/");
        const teachers = await fetchAPI("/teachers/");
        
        // Prepare global caching for modal submission
        window.tempClasses = classes;
        window.tempTeachers = teachers;
        window.activeScheduleClassId = classes && classes.length > 0 ? classes[0].id : null;
        
        let htmlBlock = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="color: #1e293b; margin:0;">Master Schedule Builder</h2>
                <select id="masterClassSelect" onchange="loadClassScheduleView(this.value)" style="padding: 10px; border-radius: 6px; border: 1px solid #cbd5e1; outline: none; font-weight: bold;">
                    ${classes && classes.length > 0 ? classes.map(c => `<option value="${c.id}">${c.name}</option>`).join('') : '<option value="">No Active Classes</option>'}
                </select>
            </div>
            <div id="scheduleGridContainer" style="background:white; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.05); overflow:hidden;">
                <!-- Dynamically Built Matrix Grid -->
            </div>
        `;
        content.innerHTML = htmlBlock;

        if (window.activeScheduleClassId) {
            window.loadClassScheduleView(window.activeScheduleClassId);
        }

    } else if (pageName === 'students') {
        const yearFilter = typeof window._adminStudentYearFilter === "string" ? window._adminStudentYearFilter : "";
        const q = yearFilter ? `?academic_year=${encodeURIComponent(yearFilter)}` : "";
        const students = await fetchAPI(`/students/${q}`);
        const metaYears = (await fetchAPI("/students/meta/academic-years")) || {};
        const defaults = (await fetchAPI("/students/meta/defaults")) || {};
        const classes = await fetchAPI("/classes/");
        const users = await fetchAPI("/auth/users");

        const parents = users ? users.filter(u => u.role === 'PARENT') : [];
        const defaultYear =
            defaults && defaults.default_academic_year ? defaults.default_academic_year : "";
        const distinctYears =
            metaYears && metaYears.academic_years && metaYears.academic_years.length
                ? metaYears.academic_years
                : defaultYear
                  ? [defaultYear]
                  : [];
        const regDueDefault = (() => {
            const d = new Date();
            d.setDate(d.getDate() + 14);
            return d.toISOString().split("T")[0];
        })();
        const parentOptionsNew =
            parents && parents.length
                ? parents.map((p) => `<option value="${p.id}">${p.full_name}</option>`).join("")
                : "";

        let htmlBlock = `<h2>Student roster & academic year</h2>`;
        htmlBlock += `<div class="admin-students-card">`;
        htmlBlock += `<div class="admin-students-year-filter">
            <label for="adminStudentYearFilter">Filter by academic year:</label>
            <select id="adminStudentYearFilter" onchange="window._adminStudentYearFilter=this.value;showPage('students');">
                <option value="">All years</option>
                ${distinctYears.map((y) => `<option value="${y}" ${yearFilter === y ? "selected" : ""}>${y}</option>`).join("")}
            </select>
        </div>`;

        htmlBlock += `<div class="admin-form-block">
            <h3>New student (current intake)</h3>
            <div class="admin-form-grid">
                <div class="admin-field">
                    <label for="newStdFirst">First name</label>
                    <input type="text" id="newStdFirst" placeholder="e.g. Sara" autocomplete="given-name">
                </div>
                <div class="admin-field">
                    <label for="newStdLast">Last name</label>
                    <input type="text" id="newStdLast" placeholder="e.g. Bekele" autocomplete="family-name">
                </div>
                <div class="admin-field">
                    <label for="newStdClass">Class</label>
                    <select id="newStdClass">
                        <option value="">Select class</option>
                        ${classes ? classes.map(c => `<option value="${c.id}">${c.name}</option>`).join('') : ''}
                    </select>
                </div>
                <div class="admin-field">
                    <label for="newStdParentInput">Linked parent</label>
                    <input type="text" id="newStdParentInput" list="parentsDatalist" placeholder="Search parent name..." autocomplete="off" title="Required for Chapa registration invoice">
                    <datalist id="parentsDatalist">
                        ${parents && parents.length ? parents.map(p => `<option value="${p.full_name} (${p.username}) - ID:${p.id}"></option>`).join("") : ""}
                    </datalist>
                </div>
                <div class="admin-field admin-field--span2">
                    <label for="newStdYear">Academic year</label>
                    <input type="text" id="newStdYear" placeholder="e.g. 2026-2027" value="${defaultYear}" title="Defaults to the current school year; edit if needed.">
                </div>
            </div>

            <div class="admin-form-actions">
                <button type="button" class="admin-btn-register" onclick="createStudent()">Register new student</button>
            </div>
        </div>`;

        htmlBlock += `<div class="admin-form-block">
            <h3>Re-enroll existing student</h3>
            <div class="admin-form-grid">
                <div class="admin-field admin-field--span2">
                    <label for="reEnrollStudentInput">Student</label>
                    <input type="text" id="reEnrollStudentInput" list="studentsDatalist" placeholder="Search student name..." autocomplete="off">
                    <datalist id="studentsDatalist">
                        ${students && students.length ? students.map(s => `<option value="${s.first_name} ${s.last_name} (${s.academic_year || '—'}) - ID:${s.id}"></option>`).join('') : ''}
                    </datalist>
                </div>
                <div class="admin-field">
                    <label for="reEnrollClassId">New class</label>
                    <select id="reEnrollClassId">
                        <option value="">Select class</option>
                        ${classes ? classes.map(c => `<option value="${c.id}">${c.name}</option>`).join('') : ''}
                    </select>
                </div>
                <div class="admin-field">
                    <label for="reEnrollYear">New academic year</label>
                    <input type="text" id="reEnrollYear" placeholder="e.g. 2026-2027">
                </div>
            </div>
            <div class="admin-form-actions">
                <button type="button" class="admin-btn-reapply" onclick="reEnrollExistingStudent()">Apply re-enrollment</button>
            </div>
        </div>`;

        htmlBlock += `<div class="admin-form-block">
            <h3>Bulk upload students (CSV/Excel)</h3>
            <div class="admin-form-grid" style="align-items: center;">
                <div class="admin-field admin-field--span2">
                    <label for="bulkUploadFile">Select file (.csv, .xlsx)</label>
                    <input type="file" id="bulkUploadFile" accept=".csv, .xlsx" style="width: 100%; padding: 8px; border: 1px dashed #cbd5e1; border-radius: 6px; background: #f8fafc;">
                    <p style="font-size: 11px; color: #64748b; margin-top: 4px;">Required columns: first_name, last_name, class_id. Optional: academic_year.</p>
                </div>
            </div>
            <div class="admin-form-actions">
                <button type="button" id="bulkUploadBtn" class="admin-btn-register" onclick="bulkUploadStudents()"><i class='bx bx-upload'></i> Upload file</button>
            </div>
        </div>`;

        htmlBlock += `<div style="display:flex; justify-content:space-between; align-items:center; margin: 20px 0 10px 0;">
            <div>
                <input type="text" id="adminStudentSearchName" placeholder="Search students by name..." onkeyup="filterAdminStudentsTable()" style="padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; width: 250px; font-size: 14px;">
            </div>
            <div>
                <select id="adminStudentClassFilter" onchange="filterAdminStudentsTable()" style="padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; min-width: 150px;">
                    <option value="">All Classes</option>
                    ${classes ? classes.map(c => `<option value="${c.name}">${c.name}</option>`).join('') : ''}
                </select>
            </div>
        </div>`;
        htmlBlock += `<div class="admin-table-scroll"><table class="admin-students-table"><thead><tr>
            <th>Name</th>
            <th>Academic year</th>
            <th>Status</th>
            <th>Class</th>
            <th>Parent</th>
            <th>Reassign class</th>
            <th>Actions</th>
        </tr></thead><tbody>`;
        
        if (students && students.length > 0) {
            students.forEach(s => {
                const pOpt = parents.map(p => `<option value="${p.id}" ${s.parent_id === p.id ? 'selected' : ''}>${p.full_name}</option>`).join('');
                const cOpt = classes.map(c => `<option value="${c.id}" ${s.class_id === c.id ? 'selected' : ''}>${c.name}</option>`).join('');
                
                htmlBlock += `<tr>
                    <td class="col-name">${s.first_name} ${s.last_name}</td>
                    <td class="col-narrow">${s.academic_year || '—'}</td>
                    <td>${s.is_active ? '<span style="color:#16a34a; font-weight:bold;">Active</span>' : '<span style="color:#eab308; font-weight:bold;">Pending</span>'}</td>
                    <td class="col-class">${s.class_room.name}</td>
                    <td><select id="parentSelect_${s.id}"><option value="">None</option>${pOpt}</select></td>
                    <td><select id="classSelect_${s.id}">${cOpt}</select></td>
                    <td>
                        <div class="admin-action-btns">
                            <button type="button" class="admin-btn-save" onclick="updateStudent(${s.id})">Save</button>
                            <button type="button" class="admin-btn-del" onclick="deleteStudent(${s.id})">Delete</button>
                        </div>
                    </td>
                </tr>`;
            });
        } else {
            htmlBlock += `<tr><td colspan="7" style="padding:24px; text-align:center; color:#64748b;">No students found for this filter.</td></tr>`;
        }
        
        htmlBlock += `</tbody></table></div></div>`;
        content.innerHTML = htmlBlock;

        window.filterAdminStudentsTable = () => {
            const nameInput = document.getElementById('adminStudentSearchName')?.value.toLowerCase() || '';
            const classInput = document.getElementById('adminStudentClassFilter')?.value || '';
            const table = document.querySelector('.admin-students-table tbody');
            if (!table) return;
            const rows = table.getElementsByTagName('tr');
            for (let i = 0; i < rows.length; i++) {
                const nameCol = rows[i].querySelector('.col-name');
                const classCol = rows[i].querySelector('.col-class');
                if (nameCol && classCol) {
                    const textName = nameCol.textContent || nameCol.innerText;
                    const textClass = classCol.textContent || classCol.innerText;
                    
                    const matchesName = textName.toLowerCase().indexOf(nameInput) > -1;
                    const matchesClass = classInput === "" || textClass.trim() === classInput;
                    
                    rows[i].style.display = (matchesName && matchesClass) ? '' : 'none';
                }
            }
        };

        window.createStudent = async () => {
            const first = document.getElementById('newStdFirst').value;
            const last = document.getElementById('newStdLast').value;
            const classId = document.getElementById('newStdClass').value;
            const yr = document.getElementById('newStdYear').value.trim();
            const parentInput = document.getElementById('newStdParentInput')?.value || '';
            const parentMatch = parentInput.match(/- ID:(\d+)$/);
            const parentVal = parentMatch ? parentMatch[1] : '';
            if (!first || !last || !classId) return alert("First name, Last Name, and Class required");
            const payload = { first_name: first, last_name: last, class_id: parseInt(classId) };
            if (yr) payload.academic_year = yr;
            if (parentVal) payload.parent_id = parseInt(parentVal, 10);

            if (!parentVal) return alert("Select a linked parent so the Accountant can process the registration fee and the parent can pay.");
            payload.create_registration_invoice = true;

            const res = await fetchAPI("/students/", { method: "POST", body: JSON.stringify(payload) });
            if (res && res.id) {
                let msg = "Student registered.";
                if (res.registration_payment_id) {
                    msg += " Registration invoice FEE-" + res.registration_payment_id + " is on the parent portal (Pay with Chapa).";
                }
                alert(msg);
                showPage('students');
            } else {
                const det = res && res.detail;
                const line = Array.isArray(det) ? det.map((d) => d.msg || JSON.stringify(d)).join(" ") : (typeof det === "string" ? det : det ? JSON.stringify(det) : "");
                alert(line || "Failed to add student. Ensure class has an assigned teacher.");
            }
        };

        window.reEnrollExistingStudent = async () => {
            const studentInput = document.getElementById('reEnrollStudentInput')?.value || '';
            const studentMatch = studentInput.match(/- ID:(\d+)$/);
            const sid = studentMatch ? studentMatch[1] : '';
            
            const cid = document.getElementById('reEnrollClassId').value;
            const yr = document.getElementById('reEnrollYear').value.trim();
            if (!sid || !cid || !yr) return alert("Select a student, new class, and academic year.");
            const res = await fetchAPI(`/students/${sid}/re-enroll`, {
                method: "POST",
                body: JSON.stringify({ class_id: parseInt(cid), academic_year: yr }),
            });
            if (res && !res.detail) {
                showPage('students');
            } else {
                alert(res && res.detail ? res.detail : "Re-enrollment failed. Check class has an assigned teacher.");
            }
        };

        window.bulkUploadStudents = async () => {
            const fileInput = document.getElementById('bulkUploadFile');
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                return alert("Please select a .csv or .xlsx file first.");
            }
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append("file", file);

            const token = localStorage.getItem("token");
            const btn = document.getElementById('bulkUploadBtn');
            const originalText = btn.innerHTML;
            btn.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i> Uploading...";
            btn.disabled = true;

            try {
                const response = await fetch("http://localhost:8000/students/bulk-upload", {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`
                    },
                    body: formData
                });
                
                const data = await response.json();
                if (response.ok) {
                    alert(data.message || "Bulk upload successful.");
                    showPage('students');
                } else {
                    alert("Upload failed: " + (data.detail || "Check file format and data."));
                }
            } catch (e) {
                alert("Network error during upload.");
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        };

        window.updateStudent = async (studentId) => {
            const classId = document.getElementById(`classSelect_${studentId}`).value;
            const parentId = document.getElementById(`parentSelect_${studentId}`).value;
            const payload = { class_id: parseInt(classId) };
            if (parentId) payload.parent_id = parseInt(parentId);
            else payload.parent_id = null;
            
            const btn = event.target;
            btn.innerText = "...";
            const res = await fetchAPI(`/students/${studentId}`, { method: "PATCH", body: JSON.stringify(payload) });
            if (res) showPage('students');
            else alert("Could not update. Target class might be unassigned.");
        };

        window.deleteStudent = async (studentId) => {
            if (!confirm("Remove this student completely?")) return;
            const res = await fetchAPI(`/students/${studentId}`, { method: "DELETE" });
            showPage('students');
        };
    } else if (pageName === 'payments') {
        const reports = await fetchAPI("/reports/financial");
        window._archivedFinancialReports = Array.isArray(reports) ? reports : [];
        let htmlBlock = `
            <h2>Archived Financial Reports</h2>
            <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px;">
        `;
        
        if (reports && reports.length > 0) {
            reports.forEach(r => {
                const efficiency = r.total_revenue > 0 || r.pending_dues > 0 ? ((r.total_revenue / (r.total_revenue + r.pending_dues)) * 100).toFixed(1) : 0;
                let dateStr = new Date(r.report_date).toLocaleDateString() + ' ' + new Date(r.report_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                
                htmlBlock += `
                    <div style="background:white; padding:20px; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.05); border-top: 4px solid #10b981;">
                        <h4 style="color:#1e293b; margin-bottom:5px;">Snapshot: ${dateStr}</h4>
                        <p style="color:#64748b; font-size:12px; margin-bottom:15px;">Generated by: ${r.generated_by.full_name}</p>
                        
                        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                            <span style="color:#64748b; font-size:14px;">Gross Cleared:</span>
                            <strong style="color:#10b981;">${r.total_revenue.toLocaleString()}.00 ETB</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                            <span style="color:#64748b; font-size:14px;">Total Pending:</span>
                            <strong style="color:#ef4444;">${r.pending_dues.toLocaleString()}.00 ETB</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                            <span style="color:#64748b; font-size:14px;">Overdue Accounts:</span>
                            <strong style="color:#ef4444;">${r.overdue_count}</strong>
                        </div>
                        
                        <div style="background:#f1f5f9; padding:10px; border-radius:6px; text-align:center;">
                            <span style="font-size:12px; color:#64748b; text-transform:uppercase;">Collection Efficiency</span><br>
                            <strong style="color:#1d4ed8; font-size:18px;">${efficiency}%</strong>
                        </div>
                        <div style="margin-top:14px;padding-top:12px;border-top:1px solid #e2e8f0;display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;">
                            <button type="button" onclick="downloadArchivedFinancialReport(${r.id})" style="font-size:12px;padding:8px 14px;background:#2563eb;color:white;border:none;border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-weight:600;">
                                <i class='bx bx-download'></i> Download CSV
                            </button>
                            <button type="button" onclick="downloadArchivedFinancialReportPng(${r.id})" style="font-size:12px;padding:8px 14px;background:white;color:#334155;border:1px solid #cbd5e1;border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-weight:600;">
                                <i class='bx bx-image'></i> Download PNG
                            </button>
                        </div>
                    </div>
                `;
            });
        } else {
            htmlBlock += `<p style="padding: 20px; color: #64748b;">No financial reports have been submitted by the Accountant yet.</p>`;
        }
        
        htmlBlock += `</div>`;
        content.innerHTML = htmlBlock;
    } else if (pageName === 'attendance') {
        const [analytics, classMetrics] = await Promise.all([
            fetchAPI("/dashboard/analytics"),
            fetchAPI("/dashboard/class-metrics"),
        ]);
        if (!analytics || !Array.isArray(analytics.windows)) {
            const msg =
                analytics && analytics.detail
                    ? typeof analytics.detail === "string"
                        ? analytics.detail
                        : JSON.stringify(analytics.detail)
                    : "Could not load attendance analytics. Check the backend and try again.";
            content.innerHTML = `<div style="max-width:560px;margin:24px auto;padding:24px;background:#fff;border-radius:12px;border:1px solid #fecaca;color:#991b1b;"><h2 style="margin:0 0 10px;font-size:1.05rem;">Attendance reports unavailable</h2><p style="margin:0;line-height:1.5;">${String(msg).replace(/</g, "&lt;")}</p></div>`;
            return;
        }

        window._schoolAttendanceAnalytics = analytics;
        window._schoolAttendanceClassMetrics = Array.isArray(classMetrics) ? classMetrics : [];

        const fmtDate = (d) => {
            if (!d) return "—";
            const s = typeof d === "string" ? d : String(d);
            return s.length >= 10 ? s.slice(0, 10) : s;
        };

        const windowCards = analytics.windows
            .map(
                (w) => `
            <div class="admin-analytics-card">
                <p class="admin-analytics-card-label">${w.label}</p>
                <p class="admin-analytics-card-range">${fmtDate(w.period_start)} → ${fmtDate(w.period_end)}</p>
                <div class="admin-analytics-card-metrics">
                    <div>
                        <span class="admin-analytics-metric-label">Absence rate</span>
                        <strong class="admin-analytics-abs">${w.absence_pct}%</strong>
                    </div>
                    <div>
                        <span class="admin-analytics-metric-label">Attendance rate</span>
                        <strong class="admin-analytics-pres">${w.attendance_pct}%</strong>
                    </div>
                </div>
                <p class="admin-analytics-card-foot">${w.present.toLocaleString()} present · ${w.absent.toLocaleString()} absent · <strong>${w.records_marked.toLocaleString()}</strong> marks recorded</p>
            </div>`,
            )
            .join("");

        const classRows =
            window._schoolAttendanceClassMetrics.length === 0
                ? `<tr><td colspan="5" style="padding:16px;color:#64748b;">No classes on file.</td></tr>`
                : window._schoolAttendanceClassMetrics
                      .map((m) => {
                          const tot = m.present_today + m.absent_today;
                          const absPct = tot === 0 ? 0 : Math.round((m.absent_today / tot) * 100);
                          return `<tr>
                        <td style="padding:12px 14px;font-weight:600;color:#1e293b;">${m.class_name}</td>
                        <td style="padding:12px 14px;color:#64748b;">${m.total_students}</td>
                        <td style="padding:12px 14px;color:#2563eb;">${m.present_today}</td>
                        <td style="padding:12px 14px;color:#ef4444;">${m.absent_today}</td>
                        <td style="padding:12px 14px;">${tot ? absPct + "%" : "—"}</td>
                    </tr>`;
                      })
                      .join("");

        content.innerHTML = `
            <div class="admin-analytics-toolbar">
                <div>
                    <h2 style="margin:0 0 8px 0;color:#1e293b;">Attendance analytics</h2>
                    <p style="margin:0;color:#64748b;font-size:14px;max-width:720px;line-height:1.5;">
                        School-wide rates from recorded marks (present + absent). <strong>As of ${fmtDate(analytics.as_of)}</strong> ·
                        <strong>${analytics.enrolled_students.toLocaleString()}</strong> students enrolled.
                    </p>
                </div>
                <button type="button" class="admin-btn-register" onclick="exportSchoolAttendanceAnalytics()"><i class='bx bx-export'></i> Export CSV</button>
            </div>

            <div class="admin-analytics-cards">
                ${windowCards}
            </div>

            <div class="admin-analytics-chart-wrap">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:16px;">
                    <h3 style="margin:0;font-size:16px;color:#1e293b;">Daily marks (school-wide)</h3>
                    <label style="font-size:13px;color:#64748b;display:flex;align-items:center;gap:8px;">
                        Show last
                        <select id="adminAttendanceTrendRange" style="padding:8px 10px;border-radius:8px;border:1px solid #cbd5e1;font-weight:600;">
                            <option value="7">7 days</option>
                            <option value="14">14 days</option>
                            <option value="30" selected>30 days</option>
                        </select>
                    </label>
                </div>
                <div style="position:relative;height:320px;width:100%;">
                    <canvas id="adminAttendanceTrendChart"></canvas>
                </div>
            </div>

            <div class="admin-analytics-chart-wrap" style="margin-bottom:0;">
                <h3 style="margin:0 0 14px 0;font-size:16px;color:#1e293b;">Today's class snapshot</h3>
                <div style="overflow-x:auto;border:1px solid #e2e8f0;border-radius:10px;">
                    <table style="width:100%;min-width:520px;border-collapse:collapse;font-size:14px;">
                        <thead>
                            <tr style="background:#f8fafc;text-align:left;">
                                <th style="padding:12px 14px;color:#64748b;font-size:11px;text-transform:uppercase;">Class</th>
                                <th style="padding:12px 14px;color:#64748b;font-size:11px;text-transform:uppercase;">Enrolled</th>
                                <th style="padding:12px 14px;color:#64748b;font-size:11px;text-transform:uppercase;">Present</th>
                                <th style="padding:12px 14px;color:#64748b;font-size:11px;text-transform:uppercase;">Absent</th>
                                <th style="padding:12px 14px;color:#64748b;font-size:11px;text-transform:uppercase;">Absence (today)</th>
                            </tr>
                        </thead>
                        <tbody>${classRows}</tbody>
                    </table>
                </div>
            </div>
        `;

        const runChart = () => {
            const canvas = document.getElementById("adminAttendanceTrendChart");
            const sel = document.getElementById("adminAttendanceTrendRange");
            if (!canvas || typeof Chart === "undefined") return;

            const days = sel ? parseInt(sel.value, 10) || 30 : 30;
            const trend = analytics.daily_trend || [];
            const slice = trend.slice(-Math.min(days, trend.length));

            const labels = slice.map((t) => {
                const d = new Date(t.date + "T12:00:00");
                return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
            });

            if (window.adminAttendanceChartInstance) {
                try {
                    window.adminAttendanceChartInstance.destroy();
                } catch (e) {}
                window.adminAttendanceChartInstance = null;
            }

            window.adminAttendanceChartInstance = new Chart(canvas, {
                type: "bar",
                data: {
                    labels,
                    datasets: [
                        {
                            label: "Present",
                            data: slice.map((t) => t.present_count),
                            backgroundColor: "#2563eb",
                            borderRadius: 4,
                        },
                        {
                            label: "Absent",
                            data: slice.map((t) => t.absent_count),
                            backgroundColor: "#94a3b8",
                            borderRadius: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1 },
                        },
                    },
                    plugins: {
                        legend: { position: "top" },
                        tooltip: {
                            callbacks: {
                                title: (items) => {
                                    const i = items[0].dataIndex;
                                    return slice[i] ? String(slice[i].date) : "";
                                },
                            },
                        },
                    },
                },
            });
        };

        const rangeEl = document.getElementById("adminAttendanceTrendRange");
        if (rangeEl) rangeEl.addEventListener("change", runChart);
        setTimeout(runChart, 80);
    } else if (pageName === "announcements") {
        const list = await fetchAPI("/announcements/");
        const classes = await fetchAPI("/classes/");
        const items = Array.isArray(list) ? list : [];
        const classesList = Array.isArray(classes) ? classes : [];
        const esc = (s) =>
            String(s ?? "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        const rows =
            items.length === 0
                ? `<p style="padding:20px;color:#64748b;">No announcements posted yet. Use the form above to notify all parents.</p>`
                : items
                      .map((a) => {
                          const when = new Date(a.created_at).toLocaleString();
                          const targetBadge = a.target_class_name ? `<span style="background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:12px; font-size:12px; margin-left:10px;">${esc(a.target_class_name)}</span>` : `<span style="background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:12px; font-size:12px; margin-left:10px;">All Parents</span>`;
                          return `<article class="admin-announce-card">
                            <header><strong>${esc(a.title)}</strong>${targetBadge}<span>${esc(when)} · ${esc(a.author_name)}</span></header>
                            <div class="admin-announce-body">${esc(a.body)}</div>
                          </article>`;
                      })
                      .join("");
        content.innerHTML = `
            <h2 style="margin:0 0 20px 0;color:#1e293b;">Parent announcements</h2>
            <div style="background:white;padding:20px;border-radius:12px;border:1px solid #e2e8f0;margin-bottom:24px;max-width:720px;">
                <h3 style="margin:0 0 14px 0;font-size:16px;color:#1e293b;">New announcement</h3>
                <label style="display:block;font-size:12px;color:#64748b;margin-bottom:6px;">Target Audience</label>
                <select id="adminAnnTargetClass" style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:14px;font-size:14px;background:#f8fafc;">
                    <option value="">All Parents (School-wide)</option>
                    ${classesList.map(c => `<option value="${c.id}">Class: ${c.name}</option>`).join('')}
                </select>
                <label style="display:block;font-size:12px;color:#64748b;margin-bottom:6px;">Title</label>
                <input type="text" id="adminAnnTitle" maxlength="200" placeholder="e.g. School closed — public holiday"
                    style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:14px;font-size:14px;">
                <label style="display:block;font-size:12px;color:#64748b;margin-bottom:6px;">Message (max 4000 characters)</label>
                <textarea id="adminAnnBody" rows="6" maxlength="4000" placeholder="Write the message parents should read…"
                    style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;resize:vertical;"></textarea>
                <button type="button" class="admin-btn-register" style="margin-top:14px;" onclick="postAdminAnnouncement()">
                    <i class='bx bx-send'></i> Send Announcement
                </button>
            </div>
            <h3 style="margin:0 0 12px 0;font-size:16px;color:#1e293b;">Posted (newest first)</h3>
            <div class="admin-announce-list">${rows}</div>
        `;

        window.postAdminAnnouncement = async () => {
            const title = document.getElementById("adminAnnTitle")?.value.trim();
            const body = document.getElementById("adminAnnBody")?.value.trim();
            const targetClassStr = document.getElementById("adminAnnTargetClass")?.value;
            const target_class_id = targetClassStr ? parseInt(targetClassStr) : null;
            
            if (!title || !body) return alert("Enter both a title and a message.");
            const res = await fetchAPI("/announcements/", {
                method: "POST",
                body: JSON.stringify({ title, body, target_class_id }),
            });
            if (res && res.id) {
                alert("Announcement published. Parents will see it under Announcements.");
                showPage("announcements");
            } else {
                const det = res && res.detail;
                const line = Array.isArray(det)
                    ? det.map((d) => d.msg || JSON.stringify(d)).join(" ")
                    : typeof det === "string"
                      ? det
                      : det
                        ? JSON.stringify(det)
                        : "";
                alert(line || "Could not publish. Ensure you have the required permissions.");
            }
        };
    }
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "../loginpag/login.html";
}

// Modal Logic
function toggleTeachingTitleFields() {
    const role = document.getElementById('roleSelect')?.value;
    const wrap = document.getElementById('teachingTitleWrap');
    if (wrap) wrap.style.display = role === 'teacher' ? 'block' : 'none';
}

function openUserModal() {
    document.getElementById('userModal').style.display = 'flex';
    toggleTeachingTitleFields();
}
function closeUserModal() { document.getElementById('userModal').style.display = 'none'; }

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('roleSelect')?.addEventListener('change', toggleTeachingTitleFields);
    document.getElementById('teachingTitleSelect')?.addEventListener('change', (e) => {
        const custom = document.getElementById('teachingTitleCustom');
        if (custom) custom.style.display = e.target.value === '__custom__' ? 'block' : 'none';
    });

    document.getElementById('addUserForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fullName = document.getElementById('addUserFullName').value.trim();
        const roleRaw = document.getElementById('roleSelect').value;
        const username = document.getElementById('addUserUsername').value.trim();
        const password = document.getElementById('addUserPassword').value;

        const roleMap = { teacher: 'TEACHER', finance: 'ACCOUNTANT', director: 'DIRECTOR', parent: 'PARENT' };
        const apiRole = roleMap[roleRaw] || roleRaw.toUpperCase();

        let teaching_title = null;
        if (apiRole === 'TEACHER') {
            const sel = document.getElementById('teachingTitleSelect').value;
            teaching_title = sel === '__custom__'
                ? document.getElementById('teachingTitleCustom').value.trim()
                : sel.trim();
            if (!teaching_title) {
                alert("Select or enter the teacher's subject specialty (e.g. Chemistry).");
                return;
            }
        }

        const body = {
            username,
            full_name: fullName,
            role: apiRole,
            password,
        };
        if (teaching_title) body.teaching_title = teaching_title;

        e.target.querySelector('button[type="submit"]').innerText = "Creating...";
        const res = await fetchAPI("/auth/register", {
            method: "POST",
            body: JSON.stringify(body),
        });

        e.target.querySelector('button[type="submit"]').innerText = "Create Account";

        if (res && !res.detail) {
            alert("User created! Username: " + username);
            closeUserModal();
            e.target.reset();
            const custom = document.getElementById('teachingTitleCustom');
            if (custom) custom.style.display = 'none';
            toggleTeachingTitleFields();
        } else {
            alert(res && res.detail ? res.detail : "Failed to create user. Username may already exist.");
        }
    });

    document.getElementById('assignScheduleForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            class_id: parseInt(window.activeScheduleClassId),
            day_of_week: document.getElementById('schedDay').value,
            period: document.getElementById('schedPeriod').value,
            subject_name: document.getElementById('schedSubject').value,
            teacher_id: parseInt(document.getElementById('schedTeacherSelect').value)
        };

        const res = await fetchAPI("/schedules/", {
            method: "POST",
            body: JSON.stringify(payload)
        });

        if (res && !res.detail) {
            closeScheduleModal();
            loadClassScheduleView(window.activeScheduleClassId);
        } else {
            alert(
                res && res.detail
                    ? (typeof res.detail === "string" ? res.detail : JSON.stringify(res.detail))
                    : "Scheduling error: collision, subject mismatch, or invalid teacher.",
            );
        }
    });
});

window.exportSchoolAttendanceAnalytics = function () {
    const data = window._schoolAttendanceAnalytics;
    if (!data || !Array.isArray(data.windows)) {
        alert("Open the Attendance Reports page first, then export.");
        return;
    }
    const esc = (v) => {
        const s = String(v ?? "");
        if (/[",\r\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
        return s;
    };
    const asOf = (data.as_of && String(data.as_of).slice(0, 10)) || new Date().toISOString().split("T")[0];
    let csv = "data:text/csv;charset=utf-8,";
    csv += "Section,Key,Label,Period Start,Period End,Present,Absent,Records Marked,Absence %,Attendance %\n";
    data.windows.forEach((w) => {
        csv += `Summary,${esc(w.key)},${esc(w.label)},${w.period_start},${w.period_end},${w.present},${w.absent},${w.records_marked},${w.absence_pct},${w.attendance_pct}\n`;
    });
    csv += "\n";
    csv += "Section,Date,Present Count,Absent Count,Total Marks\n";
    (data.daily_trend || []).forEach((d) => {
        const t = (d.present_count || 0) + (d.absent_count || 0);
        csv += `Daily,${d.date},${d.present_count},${d.absent_count},${t}\n`;
    });
    csv += "\n";
    csv += "Section,Class Name,Enrolled,Present Today,Absent Today,Absence Rate Today %\n";
    (window._schoolAttendanceClassMetrics || []).forEach((m) => {
        const tot = (m.present_today || 0) + (m.absent_today || 0);
        const rate = tot === 0 ? "" : Math.round(((m.absent_today || 0) / tot) * 100);
        csv += `Class snapshot,${esc(m.class_name)},${m.total_students},${m.present_today},${m.absent_today},${rate}\n`;
    });

    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csv));
    link.setAttribute("download", `Attendance_analytics_${asOf}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

window.exportAdminCSV = function() {
    if (!window.currentAdminMetrics || window.currentAdminMetrics.length === 0) {
        alert("No metrics data available to export.");
        return;
    }
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Class Name,Total Enrolled,Present Today,Absent Today,Attendance Rate (%)\n";
    
    window.currentAdminMetrics.forEach(m => {
        const total = m.present_today + m.absent_today;
        const rate = total === 0 ? 0 : Math.round((m.present_today / total) * 100);
        csvContent += `"${m.class_name}",${m.total_students},${m.present_today},${m.absent_today},${rate}%\n`;
    });
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Admin_Class_Metrics_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

window._archivedFinancialReports = [];

window.downloadArchivedFinancialReport = function (reportId) {
    const r = window._archivedFinancialReports.find((x) => x.id === reportId);
    if (!r) return;
    const efficiency =
        r.total_revenue > 0 || r.pending_dues > 0
            ? ((r.total_revenue / (r.total_revenue + r.pending_dues)) * 100).toFixed(1)
            : "0";
    const esc = (v) => {
        const s = String(v ?? "");
        if (/[",\r\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
        return s;
    };
    const genName = r.generated_by ? r.generated_by.full_name : "";
    const snapIso = r.report_date ? new Date(r.report_date).toISOString() : "";
    const header =
        "Report ID,Report Date (UTC),Gross Cleared ETB,Total Pending ETB,Overdue Accounts,Collection Efficiency %,Generated By\n";
    const line = [
        r.id,
        esc(snapIso),
        Number(r.total_revenue).toFixed(2),
        Number(r.pending_dues).toFixed(2),
        r.overdue_count,
        efficiency,
        esc(genName),
    ].join(",");
    const blob = new Blob(["\uFEFF" + header + line + "\n"], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Financial_report_${r.id}_${snapIso.slice(0, 10) || "nodate"}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
};

window.downloadArchivedFinancialReportPng = function (reportId) {
    const r = window._archivedFinancialReports.find((x) => x.id === reportId);
    if (!r) return;
    const efficiency =
        r.total_revenue > 0 || r.pending_dues > 0
            ? ((r.total_revenue / (r.total_revenue + r.pending_dues)) * 100).toFixed(1)
            : "0";
    const genName = r.generated_by ? r.generated_by.full_name : "—";
    const dateStr = r.report_date
        ? new Date(r.report_date).toLocaleString(undefined, {
              dateStyle: "medium",
              timeStyle: "short",
          })
        : "—";

    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const W = 640;
    const H = 400;
    const canvas = document.createElement("canvas");
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#10b981";
    ctx.fillRect(0, 0, W, 5);
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, W - 1, H - 1);

    let y = 36;
    ctx.fillStyle = "#1e293b";
    ctx.font = "600 18px system-ui, Segoe UI, sans-serif";
    ctx.fillText("EB Academy — Financial report snapshot", 28, y);
    y += 28;
    ctx.font = "14px system-ui, Segoe UI, sans-serif";
    ctx.fillStyle = "#64748b";
    ctx.fillText("Snapshot: " + dateStr, 28, y);
    y += 22;
    ctx.fillText("Generated by: " + genName, 28, y);
    y += 34;

    const moneyRow = (label, valueEtB, color) => {
        ctx.fillStyle = "#64748b";
        ctx.font = "14px system-ui, Segoe UI, sans-serif";
        ctx.fillText(label, 28, y);
        ctx.fillStyle = color;
        ctx.font = "600 14px system-ui, Segoe UI, sans-serif";
        const val = `${Number(valueEtB).toLocaleString()}.00 ETB`;
        ctx.fillText(val, W - 28 - ctx.measureText(val).width, y);
        y += 28;
    };
    moneyRow("Gross cleared", r.total_revenue, "#059669");
    moneyRow("Total pending", r.pending_dues, "#dc2626");
    ctx.fillStyle = "#64748b";
    ctx.font = "14px system-ui, Segoe UI, sans-serif";
    ctx.fillText("Overdue accounts", 28, y);
    ctx.fillStyle = "#dc2626";
    ctx.font = "600 14px system-ui, Segoe UI, sans-serif";
    const oc = String(r.overdue_count);
    ctx.fillText(oc, W - 28 - ctx.measureText(oc).width, y);
    y += 32;

    ctx.fillStyle = "#f1f5f9";
    ctx.fillRect(28, y, W - 56, 72);
    ctx.fillStyle = "#64748b";
    ctx.font = "600 11px system-ui, Segoe UI, sans-serif";
    const cap = "COLLECTION EFFICIENCY";
    ctx.fillText(cap, (W - ctx.measureText(cap).width) / 2, y + 24);
    ctx.fillStyle = "#1d4ed8";
    ctx.font = "700 22px system-ui, Segoe UI, sans-serif";
    const effText = efficiency + "%";
    ctx.fillText(effText, (W - ctx.measureText(effText).width) / 2, y + 54);

    canvas.toBlob(
        (blob) => {
            if (!blob) return;
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            const snap = r.report_date ? new Date(r.report_date).toISOString().slice(0, 10) : "nodate";
            link.href = url;
            link.download = `Financial_report_${r.id}_${snap}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        },
        "image/png",
        0.95,
    );
};

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const me = await hydrateCurrentUserHeader({
            roleEl: document.getElementById("header-user-role"),
            subtitleEl: document.getElementById("header-user-name"),
            imgEl: document.getElementById("header-user-avatar"),
        });
        const r = me && me.role ? String(me.role).trim().toUpperCase() : "";
        window._adminPortalRole = r;
        
        if (r === "ADMIN") {
            const ids = ["nav-schedules", "nav-classes", "nav-students", "nav-payments", "nav-attendance", "nav-announcements"];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = "none";
            });
        } else if (r === "DIRECTOR") {
            const navUsers = document.getElementById("nav-users");
            if (navUsers) navUsers.style.display = "none";
        }
        
        await showPage("dashboard");
    } catch (err) {
        console.error("Admin portal failed to initialize", err);
        const content = document.getElementById("dynamic-content");
        if (content) {
            content.innerHTML =
                '<div style="max-width:560px;margin:40px auto;padding:24px;background:#fff;border-radius:12px;border:1px solid #fecaca;color:#991b1b;"><h2 style="margin:0 0 12px 0;font-size:1.1rem;">Something went wrong</h2><p style="margin:0;line-height:1.5;">Open the browser developer console (F12) for details, or refresh after confirming the backend is running.</p></div>';
        }
    }
});

window.closeScheduleModal = () => {
    document.getElementById('scheduleModal').style.display = 'none';
};

window.refreshScheduleTeacherDropdown = () => {
    const select = document.getElementById("schedTeacherSelect");
    if (!select) return;
    select.innerHTML = '<option value="">-- Select teacher --</option>';
    if (!Array.isArray(window.tempTeachers)) return;
    window.tempTeachers.forEach((t) => {
        const label = t.teaching_title
            ? `${t.full_name} (${t.teaching_title})`
            : `${t.full_name} (no specialty on file)`;
        select.innerHTML += `<option value="${t.id}">${label}</option>`;
    });
};

window._onSchedTeacherChange = function () {
    const select = document.getElementById("schedTeacherSelect");
    const subj = document.getElementById("schedSubject");
    if (!select || !subj) return;
    const id = parseInt(select.value, 10);
    if (!id || !Array.isArray(window.tempTeachers)) {
        subj.value = "";
        subj.readOnly = true;
        subj.placeholder = "Select a teacher first";
        subj.style.background = "#f8fafc";
        return;
    }
    const t = window.tempTeachers.find((x) => x.id === id);
    const title = t && t.teaching_title ? String(t.teaching_title).trim() : "";
    subj.value = title;
    if (title) {
        subj.readOnly = true;
        subj.placeholder = "";
        subj.style.background = "#f8fafc";
    } else {
        subj.readOnly = false;
        subj.placeholder = "Enter subject (teacher has no specialty on file)";
        subj.style.background = "#fff";
    }
};

window.openScheduleModal = (day, period) => {
    document.getElementById("schedDay").value = day;
    document.getElementById("schedPeriod").value = period;
    document.getElementById("scheduleModalLabel").innerText = day + " at " + period;

    const subjEl = document.getElementById("schedSubject");
    if (subjEl) {
        subjEl.value = "";
        subjEl.readOnly = true;
        subjEl.placeholder = "Select a teacher first";
        subjEl.style.background = "#f8fafc";
    }
    window.refreshScheduleTeacherDropdown();
    const select = document.getElementById("schedTeacherSelect");
    if (select) {
        select.value = "";
        select.onchange = window._onSchedTeacherChange;
    }

    document.getElementById("scheduleModal").style.display = "flex";
};

window.loadClassScheduleView = async (classId) => {
    window.activeScheduleClassId = classId;
    const scheduleData = await fetchAPI('/schedules/classroom/' + classId);
    
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
    const periods = [
        "Period 1 (8:30-9:15)",
        "Period 2 (9:15-10:00)",
        "Break (10:00-10:15)",
        "Period 3 (10:15-11:00)",
        "Period 4 (11:00-11:45)",
        "Period 5 (11:45-12:30)",
        "Lunch (12:30-13:30)",
        "Period 6 (13:30-14:15)",
        "Period 7 (14:15-15:00)"
    ];

    const isBreak = (p) => p.startsWith("Break") || p.startsWith("Lunch");

    let tbl = '<table style="width:100%; border-collapse:collapse; text-align:center;">';
    tbl += '<tr><th style="padding:15px; background:#f8fafc; border-bottom:1px solid #e2e8f0; width:15%;">Time</th>';
    days.forEach(d => {
        tbl += '<th style="padding:15px; background:#f8fafc; border-bottom:1px solid #e2e8f0;">' + d + '</th>';
    });
    tbl += '</tr>';

    periods.forEach(p => {
        tbl += '<tr>';
        tbl += '<td style="padding:15px; border-bottom:1px solid #f1f5f9; font-weight:bold; color:#64748b; background:#fcfcfc;">' + p.split(" (")[0] + '<br><span style="font-size:11px; font-weight:normal;">' + p.split("(")[1].replace(")","") + '</span></td>';
        
        if (isBreak(p)) {
            tbl += '<td colspan="5" style="padding:15px; border-bottom:1px solid #f1f5f9; background:#f1f5f9; color:#94a3b8; font-style:italic;">' + p.split(" (")[0] + '</td>';
        } else {
            days.forEach(d => {
                const match = scheduleData ? scheduleData.find(s => s.day_of_week === d && s.period === p.split(" ")[1]) : null;
                if (match) {
                    tbl += '<td onclick="openScheduleModal(\'' + d + '\', \'' + p.split(" ")[1] + '\')" style="padding:15px; border-bottom:1px solid #f1f5f9; cursor:pointer; transition:0.2s; background:#eff6ff; border:1px solid #bfdbfe;"><strong style="color:#1d4ed8; display:block; font-size:14px;">' + match.subject_name + '</strong><span style="color:#64748b; font-size:12px;">' + match.teacher.full_name + '</span></td>';
                } else {
                    tbl += '<td onclick="openScheduleModal(\'' + d + '\', \'' + p.split(" ")[1] + '\')" style="padding:15px; border-bottom:1px solid #f1f5f9; border-left:1px dashed #e2e8f0; cursor:pointer; color:#cbd5e1; transition:0.2s; font-size:24px; font-weight:100;">+</td>';
                }
            });
        }
        tbl += '</tr>';
    });
    tbl += '</table>';

    document.getElementById('scheduleGridContainer').innerHTML = tbl;
};