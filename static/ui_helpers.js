/* static/ui_helpers.js */

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 5000);
}

async function showConfirmDialog({ title, details, confirmText = 'Confirm', cancelText = 'Cancel', confirmClass = 'btn-primary' }) {
    return new Promise(resolve => {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog-overlay';

        let detailsHtml = '';
        if (details) {
            detailsHtml = Object.entries(details).map(([key, value]) => `
                <div class="confirm-detail">
                    <span class="confirm-key">${escapeHtml(key)}:</span>
                    <span class="confirm-value">${escapeHtml(value)}</span>
                </div>
            `).join('');
        }

        dialog.innerHTML = `
            <div class="confirm-dialog">
                <h3 class="confirm-title">${escapeHtml(title)}</h3>
                <div class="confirm-details">${detailsHtml}</div>
                <div class="confirm-actions">
                    <button class="btn btn-secondary" id="confirmCancel">${escapeHtml(cancelText)}</button>
                    <button class="btn ${confirmClass}" id="confirmProceed">${escapeHtml(confirmText)}</button>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);

        const closeDialog = (result) => {
            dialog.classList.add('fade-out');
            setTimeout(() => {
                document.body.removeChild(dialog);
                resolve(result);
            }, 300);
        };

        document.getElementById('confirmProceed').onclick = () => closeDialog(true);
        document.getElementById('confirmCancel').onclick = () => closeDialog(false);
        dialog.onclick = (e) => {
            if (e.target === dialog) {
                closeDialog(false);
            }
        };
    });
}

function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/[&<>"']/g, function(match) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[match];
    });
}
