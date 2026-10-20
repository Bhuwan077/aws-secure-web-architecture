// Modal Handling
function openExpenseModal() {
    const modal = document.getElementById('expenseModal');
    if (modal) {
        modal.style.display = 'flex';
        const titleInput = modal.querySelector('input[name="title"]');
        if (titleInput) {
            setTimeout(() => titleInput.focus(), 50);
        }
    }
}

function closeExpenseModal() {
    const modal = document.getElementById('expenseModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Close modal on escape key or clicking backdrop
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeExpenseModal();
    }
});

document.addEventListener('click', function(event) {
    const modal = document.getElementById('expenseModal');
    if (event.target === modal) {
        closeExpenseModal();
    }
});

// Periodic Async Healthcheck Ping
async function updateHealthBadge() {
    const badge = document.getElementById('health-badge');
    if (!badge) return;

    try {
        const response = await fetch('/healthz', { cache: 'no-store' });
        if (response.ok) {
            badge.innerHTML = '<span class="pulse-dot"></span> Health: OK';
            badge.style.color = '#34d399';
        } else {
            badge.innerHTML = '<span class="pulse-dot" style="background:#ef4444;"></span> Health: Degraded';
            badge.style.color = '#f87171';
        }
    } catch (e) {
        badge.innerHTML = '<span class="pulse-dot" style="background:#ef4444;"></span> Health: Offline';
        badge.style.color = '#f87171';
    }
}

// Run health ping on page load and every 30 seconds
document.addEventListener('DOMContentLoaded', () => {
    updateHealthBadge();
    setInterval(updateHealthBadge, 30000);
});
