// Download chat functionality
var selectionMode = false;
var selectedMessages = new Set();

// Initialize download button
document.addEventListener('DOMContentLoaded', () => {
    const downloadChatBtnBottom = document.getElementById('downloadChatBtnBottom');
    const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
    const cancelSelectionBtn = document.getElementById('cancelSelectionBtn');
    
    if (downloadChatBtnBottom) {
        downloadChatBtnBottom.addEventListener('click', toggleSelectionMode);
    }
    
    if (downloadSelectedBtn) {
        downloadSelectedBtn.addEventListener('click', downloadSelectedMessages);
    }
    
    if (cancelSelectionBtn) {
        cancelSelectionBtn.addEventListener('click', toggleSelectionMode);
    }
    
    // Re-add checkboxes after history loads
    setTimeout(() => {
        if (selectionMode) {
            addCheckboxesToMessages();
        }
    }, 500);
});

function toggleSelectionMode() {
    selectionMode = !selectionMode;
    const chatMessages = document.getElementById('chatMessages');
    const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
    const cancelSelectionBtn = document.getElementById('cancelSelectionBtn');
    
    if (selectionMode) {
        chatMessages.classList.add('selection-mode');
        downloadSelectedBtn.style.display = 'block';
        cancelSelectionBtn.style.display = 'block';
        downloadSelectedBtn.disabled = true;
        // Add checkboxes to all messages
        addCheckboxesToMessages();
    } else {
        chatMessages.classList.remove('selection-mode');
        downloadSelectedBtn.style.display = 'none';
        cancelSelectionBtn.style.display = 'none';
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
        
        message.insertBefore(checkbox, message.firstChild);
    });
    updateDownloadButton();
}

function removeCheckboxesFromMessages() {
    const checkboxes = document.querySelectorAll('.message-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.remove();
    });
}

function updateDownloadButton() {
    const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');
    if (downloadSelectedBtn && selectedMessages.size > 0) {
        downloadSelectedBtn.disabled = false;
        downloadSelectedBtn.textContent = `Download Selected (${selectedMessages.size})`;
    } else if (downloadSelectedBtn) {
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

