document.addEventListener('DOMContentLoaded', function() {
    console.log("Chatbot page loaded");
    
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const languageSelect = document.getElementById('language-select');
    const connectionStatus = document.getElementById('connection-status');
    const statusIcon = connectionStatus.querySelector('i');
    
    // Ensure input is always enabled
    userInput.disabled = false;
    sendButton.disabled = false;
    
    console.log("Input elements enabled");
    
    // Use consistent origin (localhost instead of 127.0.0.1)
    const rasaServerUrl = 'http://localhost:5005/webhooks/rest/webhook';
    let userEmail = localStorage.getItem("userEmail");
    let senderId = userEmail || 'default_user';
    
    console.log("User email:", userEmail);
    console.log("Sender ID:", senderId);
    
    // Initialize connection status
    updateConnectionStatus('connecting');
    
    // Check initial connection
    checkConnection();
    
    // Set the email slot in Rasa when the chat starts (no prompt) - in background
    async function setEmailSlot() {
        if (userEmail) {
            try {
                console.log("Setting email slot for:", userEmail);
                const response = await fetch("http://localhost:5005/conversations/" + encodeURIComponent(senderId) + "/tracker/events", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        event: "slot",
                        name: "email",
                        value: userEmail
                    })
                });
                
                if (response.ok) {
                    console.log("Email slot set successfully");
                } else {
                    console.error("Failed to set email slot, status:", response.status);
                }
            } catch (error) {
                console.error("Failed to set email slot:", error);
            }
        } else {
            console.log("No user email found in localStorage");
        }
    }

    // Set slot in background without blocking UI
    setEmailSlot();
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
    languageSelect.addEventListener('change', handleLanguageChange);

    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;
        
        console.log("Sending message:", message);
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
                <div class="message-content">
                    ${text}
                    <div class="buttons-container">
                        <button class="confirm-button">Confirm</button>
                        <button class="cancel-button">Cancel</button>
                    </div>
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
            console.log("Sending to Rasa:", message);
            const response = await fetch(rasaServerUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
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
            console.log("Rasa response:", data);
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
                const isDraft = response.text.includes("Here is your draft email");
                const isConfirmationPrompt = response.text.includes("Would you like me to send this complaint");
                const isFinalConfirmation = response.text.includes("✅ Complaint registered successfully");
    
                if (isDraft) {
                    addBotMessage(response.text, false);  // Show draft only
                } else if (isConfirmationPrompt) {
                    addBotMessage(response.text, true);   // Show confirm/cancel buttons
                } else if (isFinalConfirmation) {
                    // Clear any leftover buttons from previous messages (optional UX polish)
                    document.querySelectorAll('.buttons-container').forEach(el => el.remove());
                    addBotMessage(response.text, false);  // Just show success, no buttons
                } else {
                    addBotMessage(response.text, false);
                }
            }
        });
    }    

    document.querySelectorAll('.buttons-container').forEach(el => el.remove());


    async function checkConnection() {
        try {
            const response = await fetch(rasaServerUrl, {
                method: 'OPTIONS',
                headers: {
                    'Origin': 'http://localhost:8000',
                    'Access-Control-Request-Method': 'POST'
                }
            });
            updateConnectionStatus(response.ok ? 'connected' : 'disconnected');
            return response.ok;
        } catch (error) {
            updateConnectionStatus('disconnected');
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
    
    console.log("Chatbot initialization complete");
});