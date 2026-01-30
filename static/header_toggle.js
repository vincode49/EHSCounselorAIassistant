// Header toggle functionality
document.addEventListener('DOMContentLoaded', () => {
    const hideHeaderBtn = document.getElementById('hideHeaderBtn');
    const showHeaderBtn = document.getElementById('showHeaderBtn');
    const chatHeader = document.querySelector('.chat-header');
    const headerContent = document.querySelector('.header-content');
    const headerButtons = document.querySelector('.header-buttons');

    if (hideHeaderBtn && chatHeader && headerContent) {
        hideHeaderBtn.addEventListener('click', () => {
            headerContent.style.display = 'none';
            hideHeaderBtn.style.display = 'none';
            if (showHeaderBtn) showHeaderBtn.style.display = 'block';
            if (headerButtons) headerButtons.classList.add('header-hidden');
        });
    }

    if (showHeaderBtn && chatHeader && headerContent) {
        showHeaderBtn.addEventListener('click', () => {
            headerContent.style.display = 'flex';
            showHeaderBtn.style.display = 'none';
            if (hideHeaderBtn) hideHeaderBtn.style.display = 'block';
            if (headerButtons) headerButtons.classList.remove('header-hidden');
        });
    }
});

