// Global scope variables to hold loaded data temporarily for batching
let currentStudents = [];
let teacherChartInstance = null;
async function showPage(pageName) {
    const content = document.getElementById('dynamic-content');

    // Update active class in sidebar
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    const activeLink = document.querySelector(`.nav-links li[onclick*="'${pageName}'"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    const token = localStorage.getItem("token");
    if (!token) return window.location.href = "../loginpag/login.html";

    if (pageName === 'dashboard') {
        content.innerHTML = `
            <div style="padding: 25px; background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); max-width: 800px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="color: #1a73e8; margin: 0;">Your Classroom Analytics</h2>
                    <select id="trendFilter" onchange="loadTrendChart(this.value)" style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; font-weight: bold; color: #1e293b; background: white; cursor: pointer;">
                        <option value="day">Day</option>
                        <option value="week" selected>Week</option>
                        <option value="month">Month</option>
                    </select>
                </div>
                <p style="color: #64748b; margin-bottom: 20px;">Tracking cumulative attendance rates for your assigned students.</p>
                <div style="position: relative; height: 350px; width: 100%;">
                    <canvas id="attendanceChart"></canvas>
                </div>
            </div>
        `;
        setTimeout(() => loadTrendChart('week'), 100);
    } else if (pageName === 'schedule') {
        content.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="color: #1e293b; margin:0;">Your Master Schedule</h2>
            </div>
            <div id="scheduleGridContainer" style="background:white; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.05); overflow:hidden;">
                <!-- Dynamically Built Matrix Grid -->
                <p style="padding:20px; text-align:center; color:#64748b;">Loading active term schedule...</p>
            </div>
        `;
        window.loadTeacherScheduleView();
    } else if (pageName === 'attendance') {
        let students = await fetchAPI("/students/");
        if (!students) students = [];
        currentStudents = students;

        const todayStr = new Date().toISOString().split('T')[0];
        let todayLogs = await fetchAPI(`/attendance/?query_date=${todayStr}`);
        if (!todayLogs) todayLogs = [];
        const hasSubmittedToday = todayLogs.length > 0;

        let html = `
            <section class="stats-grid" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 2rem;">
                <div class="card" style="background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); text-align: center;">
                    <p style="color: #64748b; font-weight: 500; text-transform: uppercase; font-size: 0.8rem;">Class Attendance Rate</p>
                    <h1 id="rate-display" style="font-size: 2.5rem; color: #1e293b; margin-top: 10px;">0%</h1>
                </div>
                <div class="card" style="background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); text-align: center;">
                    <p style="color: #64748b; font-weight: 500; text-transform: uppercase; font-size: 0.8rem;">Total Students</p>
                    <h1 id="total-display" style="font-size: 2.5rem; color: #1e293b; margin-top: 10px;">${students.length}</h1>
                </div>
                <div class="card" style="background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); text-align: center; border-bottom: 4px solid #10b981;">
                    <p style="color: #10b981; font-weight: 500; text-transform: uppercase; font-size: 0.8rem;">Present</p>
                    <h1 id="present-display" style="font-size: 2.5rem; color: #10b981; margin-top: 10px;">0</h1>
                </div>
                <div class="card" style="background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); text-align: center; border-bottom: 4px solid #ef4444;">
                    <p style="color: #ef4444; font-weight: 500; text-transform: uppercase; font-size: 0.8rem;">Absent</p>
                    <h1 id="absent-display" style="font-size: 2.5rem; color: #ef4444; margin-top: 10px;">0</h1>
                </div>
            </section>

            <section style="background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1.5rem;">
                <h3 style="font-size: 1.1rem; color: #1e293b; margin: 0 0 6px 0;">Export attendance by date</h3>
                <p style="color: #64748b; font-size: 13px; margin: 0 0 14px 0;">Choose a day (or step with arrows) and download a CSV for that day's saved records.</p>
                <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
                    <button type="button" onclick="shiftAttendanceExportDate(-1)" style="background: white; border: 1px solid #e2e8f0; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; color: #334155;">
                        <i class="fas fa-chevron-left"></i> Previous day
                    </button>
                    <input type="date" id="attendance-export-date" value="${todayStr}" max="${todayStr}" style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-weight: 600; color: #1e293b; cursor: pointer;">
                    <button type="button" onclick="shiftAttendanceExportDate(1)" style="background: white; border: 1px solid #e2e8f0; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; color: #334155;">
                        Next day <i class="fas fa-chevron-right"></i>
                    </button>
                    <button type="button" onclick="downloadAttendanceForExportDate()" style="background: #2563eb; color: white; border: none; padding: 8px 18px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; display: inline-flex; align-items: center; gap: 8px;">
                        <i class="fas fa-file-download"></i> Download CSV for selected day
                    </button>
                </div>
                <p id="attendance-export-date-hint" style="font-size: 12px; color: #64748b; margin: 12px 0 0 0;"></p>
            </section>

            <section style="background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 15px;">
                    <h3 style="font-size: 1.2rem; color: #1e293b;">Daily Attendance Sheet</h3>
                    <div style="display: flex; gap: 10px;">
                        ${hasSubmittedToday ? `<span style="background:#fef3c7; color:#d97706; padding:8px 15px; border-radius:8px; font-weight:600; font-size:13px;"><i class="fas fa-lock"></i> Locked for Today</span>` : 
                        `<button id="mark-all-btn" onclick="markAllPresent()" style="background: white; border: 1px solid #e2e8f0; padding: 8px 15px; border-radius: 8px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 5px;">
                            <i class="fas fa-check-circle" style="color:#10b981"></i> Mark All Present
                        </button>`}
                    </div>
                </div>

                <table style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <th style="padding: 15px 10px; color: #64748b; font-size: 0.8rem; letter-spacing: 1px;">STUDENT ID</th>
                            <th style="color: #64748b; font-size: 0.8rem; letter-spacing: 1px;">FULL NAME</th>
                            <th style="text-align: right; padding-right: 40px; color: #64748b; font-size: 0.8rem; letter-spacing: 1px;">ATTENDANCE ACTION</th>
                        </tr>
                    </thead>
                    <tbody id="student-rows">
                    </tbody>
                </table>

                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 10px; margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                    ${!hasSubmittedToday ? 
                    `<button id="submit-attendance-btn" onclick="submitDatabaseBatch()" style="background: #2563eb; color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                        <i class="fas fa-paper-plane"></i> Submit Attendance
                    </button>` : ''}
                    <div id="export-container" style="display:${hasSubmittedToday ? 'block' : 'none'}; text-align:right;">
                        ${hasSubmittedToday ? `<button onclick="generateExcelCSV(window.lastSubmittedBatch, '${todayStr}')" style="background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; display:flex; align-items:center; gap:8px;">
                            <i class="fas fa-file-excel"></i> Download Report Archive - ${todayStr}
                        </button>` : ''}
                    </div>
                </div>
            </section>
        `;

        content.innerHTML = html;

        window.shiftAttendanceExportDate = function (delta) {
            const input = document.getElementById('attendance-export-date');
            if (!input) return;
            const maxStr = new Date().toISOString().split('T')[0];
            const d = new Date(input.value + 'T12:00:00');
            d.setDate(d.getDate() + delta);
            let next = d.toISOString().split('T')[0];
            if (next > maxStr) next = maxStr;
            input.value = next;
            const hint = document.getElementById('attendance-export-date-hint');
            if (hint) hint.textContent = '';
        };

        window.downloadAttendanceForExportDate = async function () {
            const input = document.getElementById('attendance-export-date');
            const hint = document.getElementById('attendance-export-date-hint');
            if (!input) return;
            const dateStr = input.value;
            if (!dateStr) {
                if (hint) hint.textContent = 'Pick a date first.';
                return;
            }
            if (hint) hint.textContent = 'Loading…';

            const logs = await fetchAPI(`/attendance/?query_date=${encodeURIComponent(dateStr)}`);
            if (!Array.isArray(logs)) {
                if (hint) hint.textContent = 'Could not load attendance. Try again.';
                return;
            }
            if (logs.length === 0) {
                if (hint) hint.textContent = 'No attendance records for ' + dateStr + '.';
                return;
            }

            const esc = (v) => {
                const s = String(v ?? '');
                if (/[",\r\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
                return s;
            };

            let csvContent = 'data:text/csv;charset=utf-8,';
            csvContent += 'Date,Student ID,First Name,Last Name,Class,Attendance Status\n';
            logs.forEach((log) => {
                const st = log.student;
                const fn = st ? st.first_name : '';
                const ln = st ? st.last_name : '';
                const cls = st && st.class_room ? st.class_room.name : '';
                csvContent += `${dateStr},${esc('EB-STD-' + log.student_id)},${esc(fn)},${esc(ln)},${esc(cls)},${log.status}\n`;
            });

            const encodedUri = encodeURI(csvContent);
            const link = document.createElement('a');
            link.setAttribute('href', encodedUri);
            link.setAttribute('download', `attendance_${dateStr}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            if (hint) hint.textContent = `Downloaded ${logs.length} row(s) for ${dateStr}.`;
        };

        const tableBody = document.getElementById('student-rows');
        
        let initialBatchData = [];

        students.forEach(student => {
            const row = document.createElement('tr');
            row.style.borderBottom = "1px solid #f8fafc";
            row.dataset.studentId = student.id;
            
            const existingLog = todayLogs.find(log => log.student_id === student.id);
            const status = existingLog ? existingLog.status : "NONE";
            row.dataset.status = status;
            
            if (existingLog) initialBatchData.push({ student_id: student.id, status: status });
            
            const pStyle = status === 'PRESENT' ? 'background:#2563eb; color:white;' : 'background:white; color:#1e293b;';
            const aStyle = status === 'ABSENT' ? 'background:#ef4444; color:white;' : 'background:white; color:#1e293b;';
            
            const initials = student.first_name[0] + student.last_name[0];
            row.innerHTML = `
                <td style="padding: 15px 10px; color: #94a3b8; font-weight: 500;">EB-STD-${student.id}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 12px; font-weight: 600;">
                        <span style="background:#eff6ff; color:#2563eb; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius:50%; font-size:11px;">
                            ${initials}
                        </span>
                        ${student.first_name} ${student.last_name}
                    </div>
                </td>
                <td style="text-align: right; padding-right: 40px;">
                    <button class="btn-p" ${hasSubmittedToday ? 'disabled' : ''} onclick="markRow(this, 'PRESENT')" style="border: 1px solid #e2e8f0; padding: 6px 15px; border-radius: 6px; cursor: ${hasSubmittedToday ? 'not-allowed' : 'pointer'}; font-weight: 600; font-size: 12px; margin-right: 5px; ${pStyle}">PRESENT</button>
                    <button class="btn-a" ${hasSubmittedToday ? 'disabled' : ''} onclick="markRow(this, 'ABSENT')" style="border: 1px solid #e2e8f0; padding: 6px 15px; border-radius: 6px; cursor: ${hasSubmittedToday ? 'not-allowed' : 'pointer'}; font-weight: 600; font-size: 12px; ${aStyle}">ABSENT</button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        if (hasSubmittedToday) {
            window.lastSubmittedBatch = initialBatchData;
            updateStats();
        }

        window.markRow = (btn, status) => {
            const row = btn.closest('tr');
            row.dataset.status = status;
            
            row.querySelector('.btn-p').style.background = "white";
            row.querySelector('.btn-p').style.color = "#1e293b";
            row.querySelector('.btn-a').style.background = "white";
            row.querySelector('.btn-a').style.color = "#1e293b";
            
            if (status === 'PRESENT') {
                btn.style.background = "#2563eb";
                btn.style.color = "white";
            } else if (status === 'ABSENT') {
                btn.style.background = "#ef4444";
                btn.style.color = "white";
            }
            updateStats();
        };

        window.markAllPresent = () => {
            document.querySelectorAll('#student-rows tr').forEach(row => {
                row.querySelector('.btn-p').click();
            });
        };

        function updateStats() {
            let presents = 0, absents = 0;
            document.querySelectorAll('#student-rows tr').forEach(row => {
                if (row.dataset.status === 'PRESENT') presents++;
                if (row.dataset.status === 'ABSENT') absents++;
            });

            document.getElementById('present-display').innerText = presents;
            document.getElementById('absent-display').innerText = absents;

            if (presents + absents > 0) {
                document.getElementById('rate-display').innerText = Math.round((presents / (presents + absents)) * 100) + "%";
            }
        }

        window.submitDatabaseBatch = async () => {
            const rows = document.querySelectorAll('#student-rows tr');
            let batch = [];
            
            rows.forEach(row => {
                const sId = row.dataset.studentId;
                const status = row.dataset.status;
                if (status !== 'NONE') {
                    batch.push({ student_id: parseInt(sId), status: status });
                }
            });

            if (batch.length === 0) return alert("No attendance marked yet.");
            
            if (batch.length !== rows.length) {
                return alert(`Missing attendance! Please explicitly mark PRESENT or ABSENT for all ${rows.length} students before submitting.`);
            }
            
            alert("Syncing batch securely to Database...");

            for (let b of batch) {
                await fetchAPI("/attendance/", {
                    method: "POST",
                    body: JSON.stringify(b)
                });
            }

            alert("Successfully saved to database!");
            
            window.lastSubmittedBatch = batch;
            const container = document.getElementById('export-container');
            const now = new Date();
            const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            container.style.display = 'block';
            container.innerHTML = `<button onclick="generateExcelCSV(window.lastSubmittedBatch, '${todayStr}')" style="background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; display:flex; align-items:center; gap:8px;">
                <i class="fas fa-file-excel"></i> Download Report - Generated ${timeStr}
            </button>`;
        };
        
        window.generateExcelCSV = function (batch, fileDateStr) {
            const esc = (v) => {
                const s = String(v ?? '');
                if (/[",\r\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
                return s;
            };
            let csvContent = "data:text/csv;charset=utf-8,";
            csvContent += "Date,Student ID,First Name,Last Name,Attendance Status\n";
            const dateCol = fileDateStr || new Date().toISOString().split('T')[0];

            batch.forEach(b => {
                const student = currentStudents.find(s => s.id == b.student_id);
                if (student) {
                    csvContent += `${dateCol},${esc('EB-STD-' + student.id)},${esc(student.first_name)},${esc(student.last_name)},${b.status}\n`;
                }
            });

            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `attendance_${dateCol}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };
    }
}

window.globalLogout = function() {
    localStorage.removeItem("token");
    window.location.href = "../loginpag/login.html";
};

document.addEventListener('DOMContentLoaded', async () => {
    await hydrateCurrentUserHeader({
        roleEl: document.getElementById("teacher-name-display"),
        subtitleEl: document.getElementById("teacher-role-subtitle"),
        imgEl: document.getElementById("teacher-avatar-img"),
    });
    showPage("dashboard");
});

window.loadTrendChart = async (timeframe) => {
    const trends = await fetchAPI(`/dashboard/teacher/attendance-trends?timeframe=${timeframe}`);
    if (!trends) return;
    if (!Array.isArray(trends)) {
        console.error("Attendance trends: expected array from API", trends);
        return;
    }

    if (teacherChartInstance) {
        teacherChartInstance.destroy();
    }

    const ctx = document.getElementById('attendanceChart');
    if (!ctx) return;

    const labels = trends.map(t => new Date(t.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
    const presentData = trends.map(t => t.present_count);
    const absentData = trends.map(t => t.absent_count);

    const presentBarColor = (context) => {
        const chart = context.chart;
        const { ctx, chartArea } = chart;
        if (!chartArea) return "#38bdf8";
        const g = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
        g.addColorStop(0, "#0284c7");
        g.addColorStop(0.45, "#38bdf8");
        g.addColorStop(1, "#7dd3fc");
        return g;
    };

    teacherChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Present',
                    data: presentData,
                    backgroundColor: presentBarColor,
                    borderRadius: 4
                },
                {
                    label: 'Absent',
                    data: absentData,
                    backgroundColor: '#ef4444',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        }
    });
};
window.loadTeacherScheduleView = async () => {
    const scheduleData = await fetchAPI('/schedules/my-schedule');
    
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
                    tbl += '<td style="padding:15px; border-bottom:1px solid #f1f5f9; background:#eff6ff; border:1px solid #bfdbfe;"><strong style="color:#1d4ed8; display:block; font-size:14px;">' + match.subject_name + '</strong><span style="color:#64748b; font-size:12px; font-weight:600;">' + match.class_room.name + '</span></td>';
                } else {
                    tbl += '<td style="padding:15px; border-bottom:1px solid #f1f5f9; border-left:1px dashed #e2e8f0; color:#cbd5e1; font-size:12px;">Free</td>';
                }
            });
        }
        tbl += '</tr>';
    });
    tbl += '</table>';

    document.getElementById('scheduleGridContainer').innerHTML = tbl;
};
