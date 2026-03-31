/* static/setup.js - Modern UI Logic */

document.addEventListener('DOMContentLoaded', () => {
    const userRole = document.getElementById('sessionContext')?.dataset.role;

    if (userRole === 'Manager') {
        // Manager-specific event listeners
        const workerForm = document.getElementById('workerForm');
        if (workerForm) {
            workerForm.addEventListener('submit', handleWorkerFormSubmit);
        }

        const shiftForm = document.getElementById('shiftForm');
        if (shiftForm) {
            shiftForm.addEventListener('submit', handleShiftFormSubmit);
        }

        const clearAllBtn = document.getElementById('clearAllBtn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', handleClearAll);
        }
    }

    // Load initial data for all roles
    loadInitialData();
});

function logout() {
    fetch('/api/logout', { method: 'POST' })
        .then(response => {
            if (response.ok) {
                window.location.href = '/';
            } else {
                console.error('Logout failed on server.');
            }
        })
        .catch(error => console.error('Logout failed:', error));
}

async function loadInitialData() {
    const userRole = document.getElementById('sessionContext')?.dataset.role;
    if (userRole === 'Manager') {
        await loadWorkers();
        await updateProceedButton();
    }
    await loadShifts();
}

// ----------------------------------------------------------------------------
// FORM HANDLERS (Manager Only)
// ----------------------------------------------------------------------------

async function handleWorkerFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    const confirmed = await showConfirmDialog({
        title: 'Confirm Worker Addition',
        details: {
            'Name': data.name || 'N/A',
            'Worker Number': data.staff_id || 'Auto-assigned',
            'Seniority': ['','Entry Level','Junior','Senior','Lead'][parseInt(data.seniority_level)] || 'N/A',
            'Hourly Rate': `$${parseFloat(data.hourly_rate).toFixed(2)}/hr`
        },
        confirmText: 'Add Worker'
    });

    if (!confirmed) return;

    try {
        const response = await fetch('/api/workers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add worker.');
        }

        showNotification('Worker added successfully!', 'success');
        e.target.reset();
        await loadWorkers();
        await updateProceedButton();
        loadBusinessInfo(); // Refresh stats
    } catch (error) {
        showNotification(error.message, 'error');
        console.error('Error adding worker:', error);
    }
}

async function handleShiftFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/shifts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create shift.');
        }

        showNotification('Shift created successfully!', 'success');
        e.target.reset();
        await loadShifts();
        await updateProceedButton();
        loadBusinessInfo(); // Refresh stats
    } catch (error) {
        showNotification(error.message, 'error');
        console.error('Error creating shift:', error);
    }
}

// ----------------------------------------------------------------------------
// DATA LOADING & RENDERING
// ----------------------------------------------------------------------------

async function loadWorkers() {
    try {
        const response = await fetch('/api/workers');
        if (!response.ok) throw new Error('Failed to fetch workers.');
        const workers = await response.json();
        
        const container = document.getElementById('workersListContent');
        if (!container) return;

        if (workers.length === 0) {
            container.innerHTML = '<p class="empty-list">No workers added yet.</p>';
            return;
        }
        
        container.innerHTML = workers.map(worker => {
            const seniorityLabels = ['', 'Entry Level', 'Junior', 'Senior', 'Lead'];
            const seniorityLabel = seniorityLabels[worker.seniority_level] || `Level ${worker.seniority_level}`;
            const skillsText = worker.skills && worker.skills.length > 0 ? worker.skills.join(', ') : 'No skills listed';
            
            return `
                <div class="worker-card">
                    <div class="worker-card-header">
                        <h3 class="worker-name">${escapeHtml(worker.name)}</h3>
                        <button class="worker-card-delete" onclick="deleteWorker('${worker.id}')" title="Delete Worker">✕</button>
                    </div>
                    <div class="worker-detail-row">
                        <span>Seniority:</span>
                        <strong>${seniorityLabel}</strong>
                    </div>
                    <div class="worker-detail-row">
                        <span>Skills:</span>
                        <strong>${escapeHtml(skillsText)}</strong>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading workers:', error);
        const container = document.getElementById('workersListContent');
        if(container) container.innerHTML = '<p class="empty-list" style="color: var(--danger-color);">Error loading workers.</p>';
    }
}

async function loadShifts() {
    try {
        const response = await fetch('/api/shifts');
        if (!response.ok) throw new Error('Failed to fetch shifts.');
        const shifts = await response.json();
        
        const container = document.getElementById('shiftsListContent');
        if (!container) return;

        if (shifts.length === 0) {
            container.innerHTML = '<p class="empty-list">No shifts created yet.</p>';
            return;
        }
        
        container.innerHTML = shifts.map(shift => {
            const startTime = shift.start_time || 'N/A';
            const endTime = shift.end_time || 'N/A';
            const skillsList = shift.required_skills && shift.required_skills.length > 0 ? shift.required_skills.join(', ') : 'None';

            return `
                <div class="list-item">
                    <div class="list-item-content">
                        <div class="list-item-title">${shift.date} • ${startTime} - ${endTime}</div>
                        <div class="list-item-detail">
                            <span>Workers Needed: <strong>${shift.required_workers}</strong></span>
                            <span>Required Skills: <strong>${escapeHtml(skillsList)}</strong></span>
                        </div>
                    </div>
                    <button class="list-item-delete" onclick="deleteShift('${shift.id}')" title="Delete Shift">Delete</button>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading shifts:', error);
        const container = document.getElementById('shiftsListContent');
        if(container) container.innerHTML = '<p class="empty-list" style="color: var(--danger-color);">Error loading shifts.</p>';
    }
}

// ----------------------------------------------------------------------------
// DELETE & CLEAR ACTIONS (Manager Only)
// ----------------------------------------------------------------------------

async function deleteWorker(workerId) {
    const confirmed = await showConfirmDialog({
        title: 'Delete Worker',
        details: { 'Confirmation': 'Are you sure you want to permanently delete this worker?' },
        confirmText: 'Delete',
        confirmClass: 'btn-danger'
    });

    if (!confirmed) return;

    try {
        const response = await fetch(`/api/workers/${workerId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete worker.');

        showNotification('Worker deleted.', 'success');
        await loadWorkers();
        await updateProceedButton();
        loadBusinessInfo();
    } catch (error) {
        showNotification(error.message, 'error');
        console.error('Error deleting worker:', error);
    }
}

async function deleteShift(shiftId) {
    const confirmed = await showConfirmDialog({
        title: 'Delete Shift',
        details: { 'Confirmation': 'Are you sure you want to delete this shift?' },
        confirmText: 'Delete',
        confirmClass: 'btn-danger'
    });

    if (!confirmed) return;

    try {
        const response = await fetch(`/api/shifts/${shiftId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete shift.');

        showNotification('Shift deleted.', 'success');
        await loadShifts();
        await updateProceedButton();
        loadBusinessInfo();
    } catch (error) {
        showNotification(error.message, 'error');
        console.error('Error deleting shift:', error);
    }
}

async function handleClearAll() {
    const confirmed = await showConfirmDialog({
        title: 'Clear All Data',
        details: { 'Warning': 'This will permanently delete ALL workers and shifts. This action cannot be undone.' },
        confirmText: 'Clear All',
        confirmClass: 'btn-danger'
    });

    if (!confirmed) return;

    try {
        const response = await fetch('/api/clear-all', { method: 'POST' });
        if (!response.ok) throw new Error('Failed to clear data.');

        showNotification('All data has been cleared.', 'success');
        await loadInitialData();
        loadBusinessInfo();
    } catch (error) {
        showNotification(error.message, 'error');
        console.error('Error clearing data:', error);
    }
}

// ----------------------------------------------------------------------------
// UI HELPERS
// ----------------------------------------------------------------------------

async function updateProceedButton() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) return;
        const stats = await response.json();
        
        const proceedBtn = document.getElementById('proceedBtn');
        if (proceedBtn) {
            proceedBtn.disabled = !(stats.total_workers > 0 && stats.total_shifts > 0);
        }
    } catch (error) {
        console.error('Error updating proceed button state:', error);
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out forwards';
        notification.addEventListener('animationend', () => notification.remove());
    }, 3000);
}

function showConfirmDialog({ title, details, confirmText, cancelText = 'Cancel', confirmClass = 'btn-primary' }) {
    return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-dialog-overlay';
        
        const detailHtml = Object.entries(details).map(([key, value]) => 
            `<p><strong>${escapeHtml(key)}:</strong> ${escapeHtml(value)}</p>`
        ).join('');

        overlay.innerHTML = `
            <div class="confirm-dialog">
                <h3>${escapeHtml(title)}</h3>
                <div class="confirm-details">${detailHtml}</div>
                <div class="confirm-actions">
                    <button class="btn btn-secondary" id="confirmCancelBtn">${escapeHtml(cancelText)}</button>
                    <button class="btn ${confirmClass}" id="confirmActionBtn">${escapeHtml(confirmText)}</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);

        document.getElementById('confirmCancelBtn').onclick = () => {
            overlay.remove();
            resolve(false);
        };
        document.getElementById('confirmActionBtn').onclick = () => {
            overlay.remove();
            resolve(true);
        };
    });
}

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
