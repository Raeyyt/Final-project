let activePage = 1;
let globalPayments = [];

window.onload = async () => {
    const d = new Date();
    document.getElementById('currentDate').innerText = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    
    // Auth Check
    const token = localStorage.getItem("token");
    if(!token) return window.location.href = "../loginpag/login.html";

    await hydrateCurrentUserHeader({
        roleEl: document.getElementById("finance-user-role"),
        subtitleEl: document.getElementById("finance-user-name"),
        imgEl: document.getElementById("finance-user-avatar"),
    });

    await fetchClasses();
    await fetchAndRenderPayments();
};

async function fetchClasses() {
    try {
        const classes = await fetchAPI("/classes/");
        if (classes) {
            const dropdown = document.getElementById("classSelect");
            dropdown.innerHTML = classes.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        }
    } catch(e) {
        console.error("Classes load failed");
    }
}

async function fetchAndRenderPayments() {
    try {
        const payments = await fetchAPI("/payments/");
        if (payments) {
            globalPayments = payments.sort((a,b) => b.id - a.id);
            renderTable();
        }
    } catch(e) {
        console.error("Failed fetching payments");
    }
}

function showSection(sectionId) {
    document.querySelectorAll('.content-view').forEach(v => v.style.display = 'none');
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    
    const target = document.getElementById(`${sectionId}-section`);
    if (target) target.style.display = 'block';
    
    // Manage sidebar active states
    const navIdMap = {
        'finance': 'nav-fin',
        'students': 'nav-stud',
        'registrations': 'nav-reg',
        'reports': 'nav-rep',
        'verify': 'nav-ver'
    };
    if (navIdMap[sectionId]) {
        document.getElementById(navIdMap[sectionId]).classList.add('active');
    }
    
    if(sectionId === 'reports') generateReport();
    if(sectionId === 'dashboard') renderDashboard();
    if(sectionId === 'registrations') renderRegistrations();
}

window.initiateVerificationTrace = async () => {
    const txRef = document.getElementById('traceInput').value.trim();
    const resultBox = document.getElementById('traceResult');
    if (!txRef) return alert("Please provide a Transaction Reference to trace.");

    resultBox.innerHTML = `<div style="text-align:center; padding:30px;"><i class='bx bx-loader-alt bx-spin' style="font-size:32px; color:#2563eb;"></i><p style="margin-top:10px; color:#64748b;">Pinging Chapa Gateway...</p></div>`;

    try {
        const res = await fetchAPI(`/payments/chapa-verify/${txRef}`);
        if(res && res.status === 'PAID') {
            resultBox.innerHTML = `
                <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:20px; border-radius:12px; border-left:5px solid #22c55e;">
                    <h3 style="color:#166534; margin-bottom:10px;"><i class='bx bxs-check-shield'></i> Success: Asset Linked</h3>
                    <p style="color:#166534; font-size:14px;">The gateway confirmed this transaction. Ledger status has been locked to PAID.</p>
                </div>
            `;
            fetchAndRenderPayments();
        } else {
            resultBox.innerHTML = `
                <div style="background:#fefce8; border:1px solid #fef08a; padding:20px; border-radius:12px; border-left:5px solid #eab308;">
                    <h3 style="color:#854d0e; margin-bottom:10px;"><i class='bx bx-error-circle'></i> Verification Failed</h3>
                    <p style="color:#854d0e; font-size:14px;">Chapa reports this transaction is still PENDING or has been ABANDONED.</p>
                </div>
            `;
        }
    } catch(e) {
        resultBox.innerHTML = `
            <div style="background:#fef2f2; border:1px solid #fecaca; padding:20px; border-radius:12px; border-left:5px solid #ef4444;">
                <h3 style="color:#991b1b; margin-bottom:10px;"><i class='bx bx-x-circle'></i> Gateway Error</h3>
                <p style="color:#991b1b; font-size:14px;">Could not reach the payment server. Please verify the Reference format.</p>
            </div>
        `;
    }
};

function renderTable() {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';

    const LIMIT = 5;
    const startIdx = (activePage - 1) * LIMIT;
    const pageData = globalPayments.slice(startIdx, startIdx + LIMIT);

    pageData.forEach(p => {
        const bStatus = p.status.toLowerCase();
        let studentStr = `<span class="cell-muted">Unknown</span>`;
        if (p.student) {
            studentStr = `<div class="cell-student"><div class="cell-primary">${p.student.first_name} ${p.student.last_name}</div><div class="cell-meta">ID: EB-STD-${p.student.id} · Class: ${p.student.class_room?.name || "—"}</div></div>`;
        }
        
        let txDisplay = p.transaction_id ? `<div class="cell-meta cell-mono">TX: ${p.transaction_id}</div>` : "";
        let actionBtn = `<button type="button" class="btn-table" onclick="openReceipt(${p.id})">View</button>`;

        if (p.status === "PENDING" && p.transaction_id) {
            actionBtn = `<button type="button" class="btn-table btn-table--warn" onclick="forceVerify('${p.transaction_id}')">Force verify</button>`;
        }

        tbody.innerHTML += `
            <tr>
                <td>${studentStr}</td>
                <td><div class="cell-amount"><div class="cell-primary">${p.amount_due.toLocaleString()}.00 ETB</div>${txDisplay}</div></td>
                <td><span class="cell-muted">Chapa Gateway</span></td>
                <td><span class="status-badge ${bStatus}">${p.status}</span></td>
                <td class="cell-actions">${actionBtn}</td>
            </tr>
        `;
    });

    // Update Cards
    const todayDate = new Date().toLocaleDateString();
    const paidToday = globalPayments.filter(p => {
        return p.status === 'PAID' && p.updated_at && new Date(p.updated_at).toLocaleDateString() === todayDate;
    });

    const totalRev = paidToday.reduce((acc, curr) => acc + curr.amount_paid, 0);
    const totalPending = globalPayments.filter(p => p.status !== 'PAID').reduce((acc, curr) => acc + curr.amount_due, 0);
    const processedCnt = paidToday.length;
    
    document.getElementById('stat-revenue').innerHTML = `${totalRev.toLocaleString()}.00 <span>ETB</span>`;
    document.getElementById('stat-pending').innerHTML = `${totalPending.toLocaleString()}.00 <span>ETB</span>`;
    document.getElementById('stat-count').innerHTML = `${processedCnt} <span>Payments</span>`;

    const totalPages = Math.ceil(globalPayments.length / LIMIT) || 1;
    document.getElementById('pageInfo').innerText = `Showing Page ${activePage} of ${totalPages}`;
}

window.forceVerify = async function(tx_ref) {
    if(!confirm("Authorize encrypted Chapa server verification? This will force ping their servers directly regardless of parent involvement.")) return;

    try {
        const res = await fetchAPI(`/payments/chapa-verify/${tx_ref}`);
        if(res && res.status === 'PAID') {
            alert("Gateway Verification Overridden: Invoice cleared uniquely by Accountant.");
            fetchAndRenderPayments();
        } else if (res) {
            alert(`Gateway Response: This physical transaction failed entirely or still holds PENDING status.`);
        }
    } catch(e) {
        alert("Verification ping violently rejected by remote gateway architecture.");
        console.error(e);
    }
};

async function generateInvoices() {
    const startDate = document.getElementById('schoolStartDate').value;
    const quarterRate = document.getElementById('annualFeeAmount').value;
    const classId = document.getElementById('classSelect').value;

    if(!startDate || !quarterRate || !classId) {
        return alert("Please input the Target Class, Quarter Start Date, and Custom Invoice Rate.");
    }

    if(!confirm(`Issue isolated quarter invoice to selected Class natively for ${quarterRate} ETB?`)) return;

    document.querySelector('.fee-card .submit-btn').innerText = "Processing Targeting Payload...";

    try {
        const res = await fetchAPI('/payments/generate', {
            method: 'POST',
            body: JSON.stringify({
                start_date: startDate,
                amount: parseFloat(quarterRate),
                class_id: parseInt(classId)
            })
        });

        if(res && res.message) {
            alert(`Success! ${res.message}`);
            await fetchAndRenderPayments();
        } else if (res && res.detail) {
            alert(`Generation Error: ${res.detail}`);
        } else {
            alert("Unknown error occurred during payload transmission.");
        }
    } catch(e) {
        alert("Error mapping isolated class invoices natively.");
        console.error(e);
    } finally {
        document.querySelector('.fee-card .submit-btn').innerText = "Run Target Invoice Generation";
    }
}

window.renderRegistrations = function() {
    const tbody = document.getElementById('registrationsBody');
    if (!tbody) return;

    // A registration fee payment is PENDING, amount_due is 0, and invoice_title is "Registration fee"
    const pendingRegs = globalPayments.filter(p => p.status === 'PENDING' && p.amount_due === 0 && p.invoice_title === 'Registration fee');

    if (pendingRegs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:#64748b;">No pending registrations at this time.</td></tr>';
        return;
    }

    const defaultDue = new Date();
    defaultDue.setDate(defaultDue.getDate() + 14);
    const defaultDueStr = defaultDue.toISOString().split('T')[0];

    tbody.innerHTML = pendingRegs.map(p => {
        const studentName = p.student ? `${p.student.first_name} ${p.student.last_name}` : 'Unknown';
        const className = p.student && p.student.class_room ? p.student.class_room.name : 'Unknown';
        
        return `
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="font-weight:600; color:#1e293b; padding:15px 10px;">${studentName}</td>
                <td><span style="background:#f1f5f9; padding:4px 8px; border-radius:4px; font-size:12px;">${className}</span></td>
                <td>
                    <input type="number" id="regAmt_${p.id}" placeholder="e.g. 5000" style="padding:8px; border:1px solid #cbd5e1; border-radius:6px; width:120px;" min="1">
                </td>
                <td>
                    <input type="date" id="regDue_${p.id}" value="${defaultDueStr}" style="padding:8px; border:1px solid #cbd5e1; border-radius:6px;">
                </td>
                <td>
                    <button class="submit-btn" style="background:#10b981; padding:8px 16px; margin:0;" onclick="approveRegistration(${p.id})">Approve Fee</button>
                </td>
            </tr>
        `;
    }).join('');
};

window.approveRegistration = async function(paymentId) {
    const amtInput = document.getElementById(`regAmt_${paymentId}`);
    const dueInput = document.getElementById(`regDue_${paymentId}`);
    
    if (!amtInput || !dueInput) return;
    
    const amount = parseFloat(amtInput.value);
    const due = dueInput.value;
    
    if (isNaN(amount) || amount <= 0) {
        return alert("Please enter a valid fee amount.");
    }
    if (!due) {
        return alert("Please enter a due date.");
    }
    
    if (!confirm(`Set registration fee to ${amount} ETB due by ${due}?`)) return;
    
    try {
        const res = await fetchAPI(`/payments/${paymentId}`, {
            method: 'PATCH',
            body: JSON.stringify({ amount_due: amount, due_date: due })
        });
        
        if (res) {
            alert("Registration fee applied. The parent can now see the invoice and pay via Chapa.");
            await fetchAndRenderPayments();
            renderRegistrations();
        } else {
            alert("Failed to update registration fee.");
        }
    } catch (e) {
        alert("An error occurred while approving registration.");
    }
};

window.exportFinanceCSV = function() {
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Invoice ID,Student Name,Grade,Amount Due,Amount Paid,Status,Due Date,Transaction Ref\n";

    globalPayments.forEach(p => {
        const studentName = p.student ? `${p.student.first_name} ${p.student.last_name}` : "Unknown";
        const grade = p.student && p.student.class_room ? p.student.class_room.name : "N/A";
        const txRef = p.transaction_id ? p.transaction_id : "N/A";

        // Escape commas in names/grades if any
        csvContent += `FEE-${p.id},"${studentName}","${grade}",${p.amount_due},${p.amount_paid},${p.status},${p.due_date},${txRef}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Finance_Ledger_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

function generateReport() {
    const totalRev = globalPayments.filter(p => p.status === 'PAID').reduce((acc, curr) => acc + curr.amount_paid, 0);
    const totalPending = globalPayments.filter(p => p.status !== 'PAID').reduce((acc, curr) => acc + curr.amount_due, 0);
    const overdueCount = globalPayments.filter(p => p.status === 'OVERDUE').length;

    const count = globalPayments.length;
    const collectionEfficiency = totalRev > 0 || totalPending > 0 ? ((totalRev / (totalRev + totalPending)) * 100).toFixed(1) : 0;

    // Stash these in global variables to send to the backend easily
    window.currentReportMetrics = {
        total_revenue: totalRev,
        pending_dues: totalPending,
        overdue_count: overdueCount
    };

    const reportBox = document.getElementById('reportSummary');

    reportBox.innerHTML = `
        <h3>Advanced Financial Matrix for ${new Date().toLocaleDateString()}</h3>
        <hr style="margin-bottom:15px; border-top:1px solid #e2e8f0;"><br>
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <p style="color:#64748b;">Gross Cleared Revenue:</p>
            <strong style="color:#10b981; font-size:16px;">${totalRev.toLocaleString()}.00 ETB</strong>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <p style="color:#64748b;">Total Outstanding Deficit:</p>
            <strong style="color:#ef4444; font-size:16px;">${totalPending.toLocaleString()}.00 ETB</strong>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <p style="color:#64748b;">Students In Overdue Status:</p>
            <strong style="color:#ef4444; font-size:16px;">${overdueCount} Accounts</strong>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:25px;">
            <p style="color:#64748b;">Total Issued Invoices:</p>
            <strong style="color:#1e293b; font-size:16px;">${count} Transactions</strong>
        </div>

        <div style="background:#f8fafc; padding:15px; border-radius:8px; margin-bottom:20px; border-left:4px solid #3b82f6;">
            <p style="color:#1d4ed8; font-weight:bold; margin-bottom:5px;">Collection Efficiency Score</p>
            <p style="color:#64748b; font-size:14px;">The academy has successfully cleared <strong>${collectionEfficiency}%</strong> of its targeted billings for the active ledger bounds.</p>
        </div>

        <div style="display:flex; gap:10px;">
            <button class="submit-btn" style="background:#2563eb;" onclick="submitReport()">Transmit Report to Director</button>
            <button class="submit-btn" style="background:#64748b;" onclick="window.print()"><i class="fas fa-print"></i> Print Snapshot</button>
        </div>
    `;
}

async function submitReport() {
    if (!window.currentReportMetrics) return;

    // Push the current metrics directly to the centralized Director Dashboard backend route
    const res = await fetchAPI("/reports/financial", {
        method: "POST",
        body: JSON.stringify(window.currentReportMetrics)
    });

    if (res) {
        alert("Success! The financial ledger snapshot has been securely forwarded to the Director's Payment Reports tab.");
    } else {
        alert("Failed to submit the report to the databank. Ensure your connection is stable.");
    }
}

function changePage(action) {
    const LIMIT = 5;
    const totalPages = Math.ceil(globalPayments.length / LIMIT) || 1;

    if (action === 'prev' && activePage > 1) {
        activePage--;
    } else if (action === 'next' && activePage < totalPages) {
        activePage++;
    }

    renderTable();
}

function openReceipt(id) {
    const p = globalPayments.find(t => t.id === id);
    if (!p) return;

    document.getElementById('receiptDetails').innerHTML = `
        <p><strong>Student:</strong> ${p.student.first_name} ${p.student.last_name}</p>
        <p><strong>Invoice ID:</strong> FEE-${p.id}</p>
        <p><strong>Amount Target:</strong> ${p.amount_due} ETB</p>
        <p><strong>Amount Dropped:</strong> ${p.amount_paid} ETB</p>
        <p><strong>Issue Base:</strong> ${new Date(p.due_date).toLocaleDateString()}</p>
        <p><strong>Status Marker:</strong> ${p.status}</p>
    `;
    document.getElementById('receiptModal').style.display = 'block';
}

function closeModal() { document.getElementById('receiptModal').style.display = 'none'; }

function renderDashboard() {
    const d = new Date();
    const dashDate = document.getElementById('dashDate');
    if (dashDate) dashDate.innerText = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    const payments = window._backupPayments || [];

    // --- Weekly Activity Chart ---
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    const days = [];
    for (let i = 6; i >= 0; i--) {
        const day = new Date();
        day.setDate(today.getDate() - i);
        days.push(day);
    }

    const dayLabels = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const weeklyData = days.map(day => {
        const dayStart = new Date(day); dayStart.setHours(0,0,0,0);
        const dayEnd = new Date(day); dayEnd.setHours(23,59,59,999);
        const dayPayments = payments.filter(p => {
            if (p.status !== 'PAID' || !p.updated_at) return false;
            const pd = new Date(p.updated_at);
            return pd >= dayStart && pd <= dayEnd;
        });
        return {
            label: dayLabels[day.getDay()],
            count: dayPayments.length,
            total: dayPayments.reduce((acc, p) => acc + p.amount_paid, 0)
        };
    });

    const maxCount = Math.max(...weeklyData.map(d => d.count), 1);
    const weekTotal = weeklyData.reduce((acc, d) => acc + d.total, 0);
    const weekCount = weeklyData.reduce((acc, d) => acc + d.count, 0);

    const chartEl = document.getElementById('weeklyChart');
    const labelsEl = document.getElementById('weeklyLabels');
    const todayLabel = dayLabels[new Date().getDay()];

    chartEl.innerHTML = weeklyData.map(d => {
        const heightPct = Math.max((d.count / maxCount) * 100, 4);
        const isToday = d.label === todayLabel;
        const barColor = isToday ? '#3b82f6' : (d.count > 0 ? '#93c5fd' : '#e2e8f0');
        return `
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; gap:4px;">
                ${d.count > 0 ? `<span style="font-size:10px; font-weight:700; color:#64748b;">${d.count}</span>` : ''}
                <div title="${d.count} payments — ${d.total.toLocaleString()} ETB"
                     style="width:100%; height:${heightPct}%; background:${barColor}; border-radius:6px 6px 0 0; transition:height 0.4s ease; cursor:default;">
                </div>
            </div>`;
    }).join('');

    labelsEl.innerHTML = weeklyData.map(d => {
        const isToday = d.label === todayLabel;
        return `<span style="flex:1; text-align:center; font-weight:${isToday ? '700' : '400'}; color:${isToday ? '#3b82f6' : '#94a3b8'};">${d.label}</span>`;
    }).join('');

    document.getElementById('dash-week-total').innerText = `${weekTotal.toLocaleString()} ETB`;
    document.getElementById('dash-week-count').innerText = weekCount;

    // --- Top Overdue Students ---
    const now = new Date(); now.setHours(0,0,0,0);
    const overdue = payments
        .filter(p => p.status !== 'PAID' && p.due_date && new Date(p.due_date) < now)
        .map(p => ({ ...p, daysOverdue: Math.floor((now - new Date(p.due_date)) / (1000 * 60 * 60 * 24)) }))
        .sort((a, b) => b.daysOverdue - a.daysOverdue)
        .slice(0, 8);

    const tbody = document.getElementById('dashOverdueBody');
    if (overdue.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#10b981; padding:30px;">
            <i class='bx bx-check-circle' style="font-size:20px; vertical-align:middle; margin-right:6px;"></i>No overdue payments!</td></tr>`;
        return;
    }

    tbody.innerHTML = overdue.map((p, i) => {
        const name = p.student ? `<strong>${p.student.first_name} ${p.student.last_name}</strong><br><small style="color:#94a3b8;">EB-STD-${p.student.id}</small>` : 'Unknown';
        const className = p.student?.class_room?.name || '—';
        const urgency = p.daysOverdue > 30 ? '#ef4444' : p.daysOverdue > 14 ? '#f97316' : '#eab308';
        return `
            <tr style="${i % 2 === 0 ? 'background:#fffbfa;' : ''}">
                <td style="color:#94a3b8; font-weight:700;">${i + 1}</td>
                <td>${name}</td>
                <td><span style="background:#f1f5f9; color:#475569; padding:3px 10px; border-radius:20px; font-size:12px;">${className}</span></td>
                <td><strong>${p.amount_due.toLocaleString()}.00 ETB</strong></td>
                <td><span style="background:${urgency}22; color:${urgency}; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700;">${p.daysOverdue}d overdue</span></td>
            </tr>`;
    }).join('');
}