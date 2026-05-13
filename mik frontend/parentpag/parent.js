let globalStudents = [];
let globalPayments = [];
let globalAttendance = [];
let activeAttendanceStudentId = null;

function escapeHtml(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem("token");
    if (!token) return window.location.href = "../loginpag/login.html";

    await hydrateCurrentUserHeader({
        roleEl: document.getElementById("parent-user-role"),
        subtitleEl: document.getElementById("parent-user-name"),
    });

    // Detect Chapa Return Link
    const urlParams = new URLSearchParams(window.location.search);
    const returningTxRef = urlParams.get('chapa_return');
    if (returningTxRef) {
        alert("Actively validating your Chapa transaction with encrypted servers...");
        try {
            const ver = await fetchAPI(`/payments/chapa-verify/${returningTxRef}`);
            if (ver && ver.status === 'PAID') {
                alert("Secure Verification Completed! Invoice marked officially as PAID.");
            } else {
                alert("Transaction returned an anomalous state or was voluntarily abandoned.");
            }
        } catch (e) {
            console.error("Verification exception", e);
        }
        window.history.replaceState({}, document.title, "parent.html");
    }

    // ID badge logout
    const idBadge = document.querySelector('.id-badge');
    if (idBadge) {
        idBadge.onclick = () => {
            if (confirm('Log out?')) {
                localStorage.removeItem("token");
                window.location.href = "../loginpag/login.html";
            }
        };
        idBadge.style.cursor = 'pointer';
        idBadge.title = 'Click to log out';
    }

    // Load data
    globalStudents   = await fetchAPI("/students/")    || [];
    globalPayments   = await fetchAPI("/payments/")    || [];
    globalAttendance = await fetchAPI("/attendance/")  || [];

    if (globalStudents.length > 0) {
        // Top-bar child selector (for fee/history sections)
        if (globalStudents.length > 1) {
            const selectorContainer = document.getElementById('childSelectorContainer');
            const selector = document.getElementById('childSelector');
            selectorContainer.style.display = 'block';
            selector.innerHTML = globalStudents.map(s =>
                `<option value="${s.id}">${s.first_name} ${s.last_name}</option>`
            ).join('');
            selector.addEventListener('change', (e) => {
                renderDashboardForStudent(parseInt(e.target.value));
            });

            // Attendance student tabs
            buildAttendanceTabs();
        }

        activeAttendanceStudentId = globalStudents[0].id;
        renderDashboardForStudent(globalStudents[0].id);
    } else {
        document.getElementById('dyn-student-name').innerText = "No Students Registered";
    }
});

// ── Build student tab pills for the attendance section ──────────────────────
function buildAttendanceTabs() {
    if (globalStudents.length <= 1) return;

    const wrap = document.getElementById('attendanceStudentSelectorWrap');
    const tabsContainer = document.getElementById('studentTabs');
    wrap.style.display = 'block';

    tabsContainer.innerHTML = globalStudents.map((s, i) => {
        const initials = `${s.first_name[0]}${s.last_name[0]}`.toUpperCase();
        return `
            <button class="student-tab ${i === 0 ? 'active-tab' : ''}"
                    onclick="selectAttendanceStudent(${s.id}, this)">
                <span class="tab-avatar">${initials}</span>
                ${s.first_name} ${s.last_name}
            </button>
        `;
    }).join('');
}

// ── Switch attendance view to a specific student ────────────────────────────
function selectAttendanceStudent(studentId, btn) {
    activeAttendanceStudentId = studentId;

    // Update tab active state
    document.querySelectorAll('.student-tab').forEach(t => t.classList.remove('active-tab'));
    if (btn) btn.classList.add('active-tab');

    renderAttendanceForStudent(studentId);
}

// ── Main render: fees + header profile ─────────────────────────────────────
function renderDashboardForStudent(studentId) {
    const student = globalStudents.find(s => s.id === studentId);
    if (!student) return;

    const gradeStr = student.class_room ? student.class_room.name : 'Unassigned';

    // Header
    document.getElementById('dyn-student-name').innerHTML =
        `Student: <strong>${student.first_name} ${student.last_name}</strong>`;
    document.getElementById('dyn-student-grade').innerText = gradeStr;
    document.getElementById('dyn-student-id').innerText = `EB-STD-${student.id}`;

    // Payments
    const studentPayments = globalPayments.filter(p => p.student_id === studentId);
    const table = document.getElementById('paymentHistoryRows');

    if (studentPayments.length > 0) {
        table.innerHTML = studentPayments.map(p => {
            const isPaid = p.status === 'PAID';
            const receiptAction = isPaid ? `<button class="btn-receipt" onclick='generateReceipt(${JSON.stringify(p)})'><i class="fa-solid fa-file-pdf"></i> Download</button>` : `<span class="text-muted">-</span>`;
            const label = (p.invoice_title && String(p.invoice_title).trim()) || 'School fee';
            return `
                <tr>
                    <td>${p.due_date}</td>
                    <td><strong>${label}</strong></td>
                    <td>FEE-${p.id}</td>
                    <td>${p.amount_due} ETB</td>
                    <td><span class="status-pill ${isPaid ? 'SUCCESSFUL' : 'PENDING'}">${p.status}</span></td>
                    <td>${receiptAction}</td>
                </tr>
            `;
        }).join('');

        const pending = studentPayments
            .filter(p => p.status !== 'PAID')
            .reduce((sum, p) => sum + p.amount_due, 0);
        document.getElementById('balanceDisplay').innerHTML = `${pending.toLocaleString()} <span>Birr</span>`;
    } else {
        if (table) table.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:30px;">No payment records found.</td></tr>`;
        document.getElementById('balanceDisplay').innerHTML = `0 <span>Birr</span>`;
    }

    // Pay button
    const payBtn = document.getElementById('payButton');
    if (payBtn) {
        const clonedBtn = payBtn.cloneNode(true);
        payBtn.parentNode.replaceChild(clonedBtn, payBtn);

        clonedBtn.addEventListener('click', async function () {
            this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
            const pendingPayment = studentPayments.find(p => p.status !== 'PAID');
            if (pendingPayment) {
                try {
                    const res = await fetchAPI(`/payments/${pendingPayment.id}/chapa-initiate`, { method: 'POST' });
                    if (!res) {
                        alert("API Request completely failed.");
                        this.innerHTML = 'Pay with Chapa';
                        return;
                    }
                    if (res && res.checkout_url) {
                        window.open(res.checkout_url, '_blank');
                        this.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Verify Payment';
                        this.style.background = '#2563eb';
                        
                        const verifyBtn = this.cloneNode(true);
                        this.parentNode.replaceChild(verifyBtn, this);

                        verifyBtn.addEventListener('click', async function () {
                            this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking...';
                            try {
                                const ver = await fetchAPI(`/payments/chapa-verify/${res.tx_ref}`);
                                if (ver && ver.status === 'PAID') {
                                    alert("Secure Verification Completed! Invoice marked officially as PAID.");
                                    window.location.reload();
                                } else {
                                    alert("Verification returned PENDING. Did you finish paying on the Chapa tab?");
                                    this.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Verify Payment';
                                }
                            } catch (e) {
                                alert("Failed to connect to verification servers.");
                                this.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Verify Payment';
                            }
                        });
                        return;
                    } else if (res && res.detail) {
                        alert(`Chapa Gateway Error: ${res.detail}`);
                        this.innerHTML = 'Pay with Chapa';
                    }
                } catch (e) {
                    alert("Chapa routing blocked. Ensure API keys are configured on the backend.");
                    this.innerHTML = 'Pay with Chapa';
                }
            } else {
                alert('No pending invoice found.');
                this.innerHTML = 'Pay with Chapa';
            }
        });
    }

    // Also render attendance for this student (default)
    activeAttendanceStudentId = studentId;
    renderAttendanceForStudent(studentId);
}

// ── Render only the attendance section for a given student ──────────────────
function renderAttendanceForStudent(studentId) {
    const studentAttendance = globalAttendance.filter(a => a.student_id === studentId);

    if (studentAttendance.length > 0) {
        let presents = 0,
            absents = 0;
        const grid = document.getElementById("attendanceGrid");

        let gridHTML = "";
        const sorted = [...studentAttendance].sort((a, b) =>
            String(a.date).localeCompare(String(b.date)),
        );
        sorted.forEach((record) => {
            if (record.status === "PRESENT") presents++;
            if (record.status === "ABSENT") absents++;

            const dotClass = record.status === "PRESENT" ? "present" : "absent";
            const raw = record.date;
            const d = new Date(
                typeof raw === "string" && raw.length >= 10 ? raw.slice(0, 10) + "T12:00:00" : raw,
            );
            const logDate = d.getDate();
            const mon = d.toLocaleDateString(undefined, { month: "short" });
            const titleStr = d.toLocaleDateString(undefined, {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
            });
            const safeTitle = titleStr.replace(/"/g, "&quot;");
            gridHTML += `<div class="day attendance-day" data-status="${record.status.toLowerCase()}" title="${safeTitle}"><span class="attendance-day-num">${logDate}</span><span class="attendance-day-mon">${mon}</span> <span class="dot ${dotClass}"></span></div>`;
        });

        document.getElementById("daysPresent").innerText = `${presents} Days`;
        document.getElementById("daysAbsent").innerText = `${absents} Days`;

        if (presents + absents > 0) {
            const rate = Math.round((presents / (presents + absents)) * 100);
            document.getElementById("attendanceRate").innerText = `${rate}%`;
        } else {
            document.getElementById("attendanceRate").innerText = `0%`;
        }

        if (grid) grid.innerHTML = gridHTML;
    } else {
        document.getElementById("daysPresent").innerText = `0 Days`;
        document.getElementById("daysAbsent").innerText = `0 Days`;
        document.getElementById("attendanceRate").innerText = `0%`;
        const grid = document.getElementById("attendanceGrid");
        if (grid)
            grid.innerHTML = `<p style="grid-column: span 7; color: #64748b; font-size:13px; text-align:center;">No attendance records found.</p>`;
    }
}

// ── Receipt Generator ───────────────────────────────────────────────────────
function generateReceipt(payment) {
    const receiptTemplate = `
    <html>
        <head>
            <title>Receipt - FEE-${payment.id}</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #1e293b; }
                .receipt-box { max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
                .header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #2563eb; padding-bottom: 20px; }
                .header h1 { color: #2563eb; margin: 0 0 10px 0; font-size: 24px; }
                .header h2 { margin: 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
                .info-row { display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px dashed #e2e8f0; padding-bottom: 10px; }
                .label { font-weight: bold; color: #64748b; }
                .value { font-weight: 600; text-align: right; }
                .total-row { display: flex; justify-content: space-between; margin-top: 30px; font-size: 20px; font-weight: bold; padding-top: 20px; border-top: 2px solid #e2e8f0; color: #2563eb; }
                .watermark { text-align: center; margin-top: 40px; font-size: 28px; font-weight: 900; color: rgba(21, 128, 61, 0.1); text-transform: uppercase; letter-spacing: 10px; transform: rotate(-5deg); }
                .footer { margin-top: 40px; text-align: center; font-size: 12px; color: #94a3b8; }
                @media print { body { -webkit-print-color-adjust: exact; padding: 0; } .receipt-box { box-shadow: none; border: none; } }
            </style>
        </head>
        <body>
            <div class="receipt-box">
                <div class="header">
                    <img src="../assets/logo_dark.png" alt="EB Academy Logo" style="width: 100px; height: auto; margin-bottom: 10px;">
                    <h1>EB ACADEMY</h1>
                    <h2>Official Payment Receipt</h2>
                </div>
                <div class="info-row">
                    <span class="label">Receipt Trace:</span>
                    <span class="value">${payment.transaction_id || `REC-FEE-${payment.id}`}</span>
                </div>
                <div class="info-row">
                    <span class="label">Date Issued:</span>
                    <span class="value">${new Date().toLocaleDateString()}</span>
                </div>
                <div class="info-row">
                    <span class="label">Billed For:</span>
                    <span class="value">${(payment.invoice_title && String(payment.invoice_title).trim()) || 'School fee'}</span>
                </div>
                <div class="info-row" style="background:#f8fafc; padding:10px; border-radius:6px; margin-top:10px; display:flex; justify-content:space-between;">
                    <div>
                        <span class="label" style="display:block; font-size:10px;">STUDENT NAME</span>
                        <span class="value" style="display:block; text-align:left; font-size:16px;">${payment.student.first_name} ${payment.student.last_name}</span>
                    </div>
                    <div style="text-align:right;">
                        <span class="label" style="display:block; font-size:10px;">STUDENT ID</span>
                        <span class="value" style="display:block; font-size:16px;">EB-STD-${payment.student.id}</span>
                    </div>
                </div>
                <div class="total-row">
                    <span>Total Amount Paid:</span>
                    <span>${payment.amount_due} ETB</span>
                </div>
                <div class="watermark">SUCCESSFULLY PAID</div>
                <div style="position:relative;">
                    <img src="../assets/stamp.png" style="position:absolute; bottom:-20px; right:20px; width:140px; opacity:0.85; transform:rotate(-5deg); z-index:10;" alt="Approved Stamp">
                </div>
                <div class="footer">
                    <p>This is a computer-generated document. No signature is required.</p>
                    <p>Processed securely via Chapa Gateway Encryption.</p>
                </div>
            </div>
            <script>window.onload = function() { window.print(); }<\/script>
        </body>
    </html>`;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(receiptTemplate);
    printWindow.document.close();
}

async function loadAnnouncements() {
    const el = document.getElementById("announcementList");
    if (!el) return;
    el.innerHTML =
        '<div style="padding:16px;text-align:center;color:#64748b;">Loading…</div>';
    const data = await fetchAPI("/announcements/");
    if (!data || !Array.isArray(data)) {
        el.innerHTML =
            '<div style="padding:20px;text-align:center;color:#64748b;">Could not load announcements. Try again later.</div>';
        return;
    }
    if (data.length === 0) {
        el.innerHTML =
            '<div style="padding:20px;text-align:center;color:#64748b;">No announcements yet. When the school posts a notice, it will appear here.</div>';
        return;
    }
    el.innerHTML = data
        .map((a) => {
            const when = new Date(a.created_at).toLocaleString();
            return `<article class="parent-announce-card">
            <header><strong>${escapeHtml(a.title)}</strong><span>${escapeHtml(when)} · ${escapeHtml(a.author_name)}</span></header>
            <div class="parent-announce-body">${escapeHtml(a.body)}</div>
        </article>`;
        })
        .join("");
}

window.showSection = function (sectionId) {
    document.querySelectorAll(".content-view").forEach((v) => (v.style.display = "none"));
    document.querySelectorAll(".nav-links li").forEach((li) => li.classList.remove("active"));
    document.getElementById(`${sectionId}-section`).style.display = "block";

    const navMap = { overview: "nav-over", announcements: "nav-ann" };
    if (navMap[sectionId]) document.getElementById(navMap[sectionId]).classList.add("active");
    if (sectionId === "announcements") loadAnnouncements();
};