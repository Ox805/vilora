// Shared API utilities

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/';
}

// Modal scroll lock — prevents body from scrolling when a modal is open
(function() {
    let scrollY = 0;

    function checkModals() {
        const anyOpen = document.querySelector('.modal[style*="display: flex"], .modal[style*="display:flex"]');
        if (anyOpen && !document.body.classList.contains('modal-open')) {
            scrollY = window.scrollY;
            document.body.classList.add('modal-open');
            document.body.style.top = `-${scrollY}px`;
        } else if (!anyOpen && document.body.classList.contains('modal-open')) {
            document.body.classList.remove('modal-open');
            document.body.style.top = '';
            window.scrollTo(0, scrollY);
        }
    }

    // Watch for modal show/hide via style changes
    const observer = new MutationObserver(checkModals);
    observer.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['style'] });
})();
