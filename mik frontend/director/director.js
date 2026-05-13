document.addEventListener('DOMContentLoaded', async function () {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../loginpag/login.html';
        return;
    }
    await hydrateCurrentUserHeader({
        roleEl: document.getElementById('director-sidebar-role'),
        subtitleEl: document.getElementById('director-sidebar-name'),
        imgEl: document.getElementById('director-sidebar-avatar'),
    });

    const dateEl = document.getElementById('director-today-date');
    if (dateEl) {
        dateEl.textContent = new Date().toLocaleDateString(undefined, {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    }
});
