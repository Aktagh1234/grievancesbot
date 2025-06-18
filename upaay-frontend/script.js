document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const languageSelect = document.getElementById('language-select');
    const connectionStatus = document.getElementById('connection-status');
    
    // Connect to Rasa server
    const rasaServerUrl = 'http://localhost:5005/webhooks/rest/webhook';
    let senderId = 'user_' + Math.random().toString(36).substr(2, 9);
    
    // Set connection status
    updateConnectionStatus('connecting');
    
    // Check server connection
    checkConnection();
    
    // Handle send button click
    sendButton.addEventListener('click', sendMessage);
    
    // Handle Enter key press
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Handle language change
    languageSelect.addEventListener('change', function() {
        const selectedLanguage = languageSelect.value;
        // You can add logic here to handle language changes if needed
        addBotMessage(`Language changed to ${languageSelect.options[languageSelect.selectedIndex].text}`);
    });
    
    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;
        
        addUserMessage(message);
        userInput.value = '';
        
        // Send message to Rasa
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
            
            // Add event listeners to buttons
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
    
    function sendToRasa(message) {
        const selectedLanguage = languageSelect.value;
        
        fetch(rasaServerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sender: senderId,
                message: message,
                metadata: {
                    language: selectedLanguage
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            updateConnectionStatus('connected');
            processRasaResponse(data);
        })
        .catch(error => {
            console.error('Error:', error);
            updateConnectionStatus('disconnected');
            addBotMessage("Sorry, I'm having trouble connecting to the server. Please try again later.");
        });
    }
    
    function processRasaResponse(responses) {
        responses.forEach(response => {
            if (response.text) {
                // Check if this is a complaint draft (simple check for longer text)
                const isComplaint = response.text.length > 100 || 
                                   response.text.includes("Here is your draft email") || 
                                   response.text.includes("Complaint registered");
                
                addBotMessage(response.text, isComplaint);
            }
            // You can handle other response types (buttons, images, etc.) here
        });
    }
    
    function checkConnection() {
        fetch(rasaServerUrl, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(() => {
            updateConnectionStatus('connected');
        })
        .catch(() => {
            updateConnectionStatus('disconnected');
        });
    }
    
    function updateConnectionStatus(status) {
        const icon = connectionStatus.querySelector('i');
        connectionStatus.className = status;
        
        switch(status) {
            case 'connected':
                icon.className = 'fas fa-circle connected';
                connectionStatus.textContent = ' Connected';
                break;
            case 'disconnected':
                icon.className = 'fas fa-circle disconnected';
                connectionStatus.textContent = ' Disconnected';
                break;
            case 'connecting':
                icon.className = 'fas fa-circle connecting';
                connectionContent = ' Connecting...';
                break;
        }
    }
    
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Initial greeting
    setTimeout(() => {
        addBotMessage("Hi I am Upay, a central India grievance chatbot. Please enter your state:");
    }, 500);
});