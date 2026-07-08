// Copier dashboard frontend scripting

document.addEventListener('DOMContentLoaded', () => {
    setupCopierToggler();
    setupModals();
});

// Setup start/stop copier toggle switch
function setupCopierToggler() {
    const toggler = document.getElementById('copier-toggle');
    if (!toggler) return;

    toggler.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const endpoint = enabled ? '/api/copier/start' : '/api/copier/stop';
        
        try {
            const res = await fetch(endpoint, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success' || data.success) {
                showToast(enabled ? 'Copier enabled' : 'Copier disabled', 'success');
                // Optional: update UI status text
                const statusText = document.getElementById('copier-status-text');
                if (statusText) {
                    statusText.innerText = enabled ? 'Active' : 'Stopped';
                    statusText.className = enabled ? 'badge badge-success' : 'badge badge-danger';
                }
            } else {
                showToast('Action failed: ' + (data.message || 'Unknown error'), 'danger');
                e.target.checked = !enabled; // revert switch state
            }
        } catch (err) {
            showToast('Network error toggling copier.', 'danger');
            e.target.checked = !enabled; // revert
        }
    });
}

// Reprocess telegram message handler
async function reprocessMessage(msgDbId) {
    if (!confirm('Are you sure you want to re-run parsing and execution checks on this message?')) return;
    
    try {
        const res = await fetch(`/api/messages/${msgDbId}/reprocess`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success' || data.success) {
            showToast('Reprocessing complete: ' + (data.message || 'Done'), 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast('Reprocessing failed: ' + (data.error || data.message || 'Unknown error'), 'danger');
        }
    } catch (err) {
        showToast('Network error reprocessing message.', 'danger');
    }
}

// Manually move trade to break-even
async function moveBreakEven(tradeDbId) {
    try {
        const res = await fetch(`/api/trades/${tradeDbId}/move-break-even`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success' || data.success) {
            showToast('Moved to break-even successfully.', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast('Action failed: ' + (data.error || data.message || 'Unknown error'), 'danger');
        }
    } catch (err) {
        showToast('Network error executing break-even.', 'danger');
    }
}

// Modal JSON viewer helpers
function setupModals() {
    const overlay = document.getElementById('modal-overlay');
    if (!overlay) return;

    // Close on click outside
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });
}

function viewJsonModal(title, jsonStringOrObj) {
    const overlay = document.getElementById('modal-overlay');
    const container = document.getElementById('modal-code-content');
    const titleEl = document.getElementById('modal-title');
    
    if (!overlay || !container || !titleEl) return;
    
    let formatted = '';
    try {
        const obj = typeof jsonStringOrObj === 'string' ? JSON.parse(jsonStringOrObj) : jsonStringOrObj;
        formatted = JSON.stringify(obj, null, 2);
    } catch (e) {
        formatted = typeof jsonStringOrObj === 'string' ? jsonStringOrObj : String(jsonStringOrObj);
    }
    
    titleEl.innerText = title;
    container.textContent = formatted;
    overlay.classList.add('active');
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// Toast alerts helper
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `glass-panel badge badge-${type}`;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '12px 24px';
    toast.style.zIndex = '9999';
    toast.style.fontSize = '0.95rem';
    toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
    toast.style.border = `1px solid ${type === 'success' ? '#00ff87' : '#ff4d6d'}`;
    toast.style.color = '#fff';
    toast.innerText = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s ease';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}
