document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const languageSelect = document.getElementById('language-select');
    const connectionStatus = document.getElementById('connection-status');
    const statusIcon = connectionStatus.querySelector('i');
    
    // Use consistent origin (localhost instead of 127.0.0.1)
    const rasaServerUrl = 'http://localhost:5005/webhooks/rest/webhook';
    let senderId = 'user_' + Math.random().toString(36).substr(2, 9);
    
    // Initialize connection status
    updateConnectionStatus('connecting');
    
    // Check initial connection
    checkConnection();
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
    languageSelect.addEventListener('change', handleLanguageChange);

    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;
        
        addUserMessage(message);
        userInput.value = '';
        sendToRasa(message);
    }

    function addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'user-message';
        messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function addBotMessage(text, isComplaint = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'bot-message';
        
        if (isComplaint) {
            messageDiv.innerHTML = `
                <div class="message-content">${text}</div>
                <div class="buttons-container">
                    <button class="confirm-button">Confirm</button>
                    <button class="cancel-button">Cancel</button>
                </div>
            `;
            
            messageDiv.querySelector('.confirm-button').addEventListener('click', function() {
                sendToRasa('confirm');
            });
            
            messageDiv.querySelector('.cancel-button').addEventListener('click', function() {
                sendToRasa('deny');
                addBotMessage('Complaint cancelled. You can start over if needed.');
            });
        } else {
            messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
        }
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function handleLanguageChange() {
        const selectedLanguage = languageSelect.value;
        addBotMessage(`Language changed to ${languageSelect.options[languageSelect.selectedIndex].text}`);
    }

    async function sendToRasa(message) {
        updateConnectionStatus('connecting');
        
        try {
            const response = await fetch(rasaServerUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    sender: senderId,
                    message: message,
                    metadata: {
                        language: languageSelect.value
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            updateConnectionStatus('connected');
            processRasaResponse(data);
        } catch (error) {
            console.error('Rasa API Error:', error);
            updateConnectionStatus('disconnected');
            addBotMessage("Sorry, I'm having trouble connecting to the server. Please try again later.");
            setTimeout(checkConnection, 3000);
        }
    }

    function processRasaResponse(responses) {
        responses.forEach(response => {
            if (response.text) {
                const isComplaint = response.text.length > 100 || 
                                   response.text.includes("Here is your draft email") || 
                                   response.text.includes("Complaint registered");
                addBotMessage(response.text, isComplaint);
            }
        });
    }

    async function checkConnection() {
        try {
            // Test with a simple GET request to a Rasa endpoint that exists
            const response = await fetch('http://localhost:5005/', {  // Changed endpoint
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                updateConnectionStatus('connected');
                setTimeout(() => {
                    addBotMessage("Hi I am Upay, a central India grievance chatbot. Please enter your state:");
                }, 500);
                return true;
            }
            throw new Error('Server responded with non-OK status');
        } catch (error) {
            console.error('Connection check failed:', error);
            updateConnectionStatus('disconnected');
            // Retry after 5 seconds (reduced from immediate retry)
            setTimeout(checkConnection, 5000);
            return false;
        }
    }
    
    function updateConnectionStatus(status) {
        connectionStatus.className = `status-${status}`;
        statusIcon.className = `fas fa-circle ${status}`;
        
        switch(status) {
            case 'connected':
                connectionStatus.innerHTML = '<i class="fas fa-circle connected"></i> Connected';
                break;
            case 'disconnected':
                connectionStatus.innerHTML = '<i class="fas fa-circle disconnected"></i> Disconnected';
                break;
            case 'connecting':
                connectionStatus.innerHTML = '<i class="fas fa-circle connecting"></i> Connecting...';
                break;
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});