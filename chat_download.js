// Download chat functionality
let selectionMode = false;
let selectedMessages = new Set();

// Initialize download button
document.addEventListener('DOMContentLoaded', () => {
    const downloadChatBtn = document.getElementById('downloadChatBtn');
    const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
    
    if (downloadChatBtn) {
        downloadChatBtn.addEventListener('click', toggleSelectionMode);
    }
    
    if (downloadSelectedBtn) {
        downloadSelectedBtn.addEventListener('click', downloadSelectedMessages);
    }
});

function toggleSelectionMode() {
    selectionMode = !selectionMode;
    const chatMessages = document.getElementById('chatMessages');
    const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
    
    if (selectionMode) {
        chatMessages.classList.add('selection-mode');
        downloadSelectedBtn.style.display = 'block';
        // Add checkboxes to all messages
        addCheckboxesToMessages();
    } else {
        chatMessages.classList.remove('selection-mode');
        downloadSelectedBtn.style.display = 'none';
        // Remove checkboxes
        removeCheckboxesFromMessages();
        selectedMessages.clear();
    }
}

function addCheckboxesToMessages() {
    const messages = document.querySelectorAll('.message');
    messages.forEach((message, index) => {
        // Skip if checkbox already exists
        if (message.querySelector('.message-checkbox')) {
            return;
        }
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'message-checkbox';
        checkbox.dataset.messageIndex = index;
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                selectedMessages.add(index);
            } else {
                selectedMessages.delete(index);
            }
            updateDownloadButton();
        });
        
        message.style.paddingLeft = '35px';
        message.insertBefore(checkbox, message.firstChild);
    });
}

function removeCheckboxesFromMessages() {
    const checkboxes = document.querySelectorAll('.message-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.parentElement.style.paddingLeft = '0';
        checkbox.remove();
    });
}

function updateDownloadButton() {
    const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
    if (selectedMessages.size > 0) {
        downloadSelectedBtn.disabled = false;
        downloadSelectedBtn.textContent = `Download Selected (${selectedMessages.size})`;
    } else {
        downloadSelectedBtn.disabled = true;
        downloadSelectedBtn.textContent = 'Download Selected';
    }
}

async function downloadSelectedMessages() {
    if (selectedMessages.size === 0) {
        alert('Please select at least one message to download.');
        return;
    }
    
    const messages = Array.from(selectedMessages).sort((a, b) => a - b);
    const messageElements = document.querySelectorAll('.message');
    const selectedContent = [];
    
    messages.forEach(index => {
        const messageEl = messageElements[index];
        if (messageEl) {
            const isUser = messageEl.classList.contains('user-message');
            const contentEl = messageEl.querySelector('.message-content');
            if (contentEl) {
                // Get text content (strip HTML tags for PDF)
                const textContent = contentEl.innerText || contentEl.textContent;
                selectedContent.push({
                    role: isUser ? 'user' : 'assistant',
                    content: textContent
                });
            }
        }
    });
    
    // Send to backend to generate PDF
    try {
        const response = await fetch('/download_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ messages: selectedContent })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chat_export_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            // Exit selection mode
            toggleSelectionMode();
        } else {
            alert('Error generating PDF. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error generating PDF. Please try again.');
    }
}

