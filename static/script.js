// Get references to elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');

// Function to add a message to the chat
function addMessage(message, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = message;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Add checkbox if in selection mode
    if (typeof selectionMode !== 'undefined' && selectionMode) {
        addCheckboxToMessage(messageDiv);
    }
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Function to add checkbox to a single message (called from chat_download.js)
function addCheckboxToMessage(messageDiv) {
    if (messageDiv.querySelector('.message-checkbox')) {
        return;
    }
    const messages = Array.from(chatMessages.querySelectorAll('.message'));
    const index = messages.indexOf(messageDiv);
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'message-checkbox';
    checkbox.dataset.messageIndex = index;
    checkbox.addEventListener('change', function() {
        if (typeof selectedMessages !== 'undefined') {
            if (this.checked) {
                selectedMessages.add(index);
            } else {
                selectedMessages.delete(index);
            }
            if (typeof updateDownloadButton !== 'undefined') {
                updateDownloadButton();
            }
        }
    });
    
    messageDiv.style.paddingLeft = '35px';
    messageDiv.insertBefore(checkbox, messageDiv.firstChild);
}

// Function to update remaining messages counter
function updateMessageCounter() {
    fetch('/get_remaining_messages')
        .then(response => response.json())
        .then(data => {
            const userInfo = document.querySelector('.user-info');
            if (userInfo) {
                const parts = userInfo.textContent.split('•');
                if (parts.length > 0) {
                    if (data.is_unlimited) {
                        userInfo.textContent = `${parts[0].trim()} • ∞ Unlimited messages`;
                    } else {
                        userInfo.textContent = `${parts[0].trim()} • 💬 ${data.remaining} messages left today`;
                    }
                }
            }

            if (!data.is_unlimited && typeof data.remaining === 'number') {
                if (data.remaining <= 0) {
                    sendButton.disabled = true;
                    userInput.disabled = true;
                    userInput.placeholder = "Daily message limit reached. Try again tomorrow!";
                } else {
                    sendButton.disabled = false;
                    userInput.disabled = false;
                    userInput.placeholder = "Type your question here... (Shift+Enter for new line)";
                }
            }
        })
        .catch(error => console.error('Error updating counter:', error));
}

// Function to load chat history
async function loadHistory() {
    try {
        const response = await fetch('/get_history');
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
            // Clear welcome message
            chatMessages.innerHTML = '';
            
            // Add all previous messages
            data.messages.forEach(msg => {
                const isUser = msg.role === 'user';
                addMessage(msg.content, isUser);
            });
            
            // Re-add checkboxes if in selection mode
            if (typeof selectionMode !== 'undefined' && selectionMode && typeof addCheckboxesToMessages !== 'undefined') {
                setTimeout(() => addCheckboxesToMessages(), 100);
            }
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Function to send message
async function sendMessage() {
    const message = userInput.value.trim();
    
    if (message === '') {
        return;
    }
    
    // Add user message to chat
    // Replace \n with <br> for display
    const displayMessage = message.replace(/\n/g, '<br>');
    addMessage(displayMessage, true);
    
    // Clear input
    userInput.value = '';
    
    // Show "thinking" message
    addMessage('Thinking...', false);
    
    try {
        // Send to backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        // Remove "thinking" message
        chatMessages.removeChild(chatMessages.lastChild);
        
        // Add bot response
        addMessage(data.response, false);
        
        // Update message counter
        updateMessageCounter();
        
        // Check if limit reached
        if (data.limit_reached) {
            sendButton.disabled = true;
            userInput.disabled = true;
            userInput.placeholder = "Daily message limit reached. Try again tomorrow!";
        }
        
    } catch (error) {
        console.error('Error:', error);
        chatMessages.removeChild(chatMessages.lastChild);
        addMessage('Sorry, something went wrong. Please try again.', false);
    }
}

// Send message on button click
sendButton.addEventListener('click', sendMessage);

// Handle Enter key
userInput.addEventListener('keydown', (event) => {
    // If Shift+Enter, allow default behavior (new line)
    if (event.key === 'Enter' && event.shiftKey) {
        return; // Let the browser handle it naturally
    }
    
    // If just Enter (no shift), send message
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Prevent default new line
        sendMessage();
    }
});

// Load chat history when page loads
window.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    updateMessageCounter();
    
    // Handle PDF download links with confirmation (using event delegation for dynamically added content)
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('pdf-download-link')) {
            e.preventDefault();
            const filename = e.target.getAttribute('data-filename');
            if (confirm(`You are about to download ${filename}. Would you like to proceed?`)) {
                window.location.href = e.target.getAttribute('href');
            }
        }
    });
});