def create_prompt_ui():
    """Create a simple HTML UI for editing the raw prompt with tabs for both bots"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prompt Editor</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            margin: 0;
            padding: 20px;
            color: #e0e0e0;
        }
        
        .main-container {
            display: flex;
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .left-panel {
            flex: 0 0 350px;
            background: #2d2d2d;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            padding: 20px;
            border: 1px solid #404040;
            height: fit-content;
        }
        
        .right-panel {
            flex: 1;
            background: #2d2d2d;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            padding: 30px;
            border: 1px solid #404040;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: #2d2d2d;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            padding: 30px;
            border: 1px solid #404040;
        }
        
        h1 {
            color: #ffffff;
            margin-bottom: 20px;
            font-size: 28px;
            text-align: center;
            font-weight: 600;
        }
        
        h2 {
            color: #ffffff;
            margin-bottom: 15px;
            font-size: 20px;
            border-bottom: 1px solid #404040;
            padding-bottom: 10px;
            font-weight: 500;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #404040;
        }
        
        .tab {
            padding: 12px 24px;
            cursor: pointer;
            border: none;
            background: none;
            color: #b0b0b0;
            font-size: 16px;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            border-radius: 4px 4px 0 0;
            font-weight: 500;
        }
        
        .tab.active {
            color: #4a9eff;
            border-bottom-color: #4a9eff;
            background: rgba(74, 158, 255, 0.1);
        }
        
        .tab:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.05);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #b0b0b0;
        }
        
        textarea {
            width: 100%;
            height: 300px;
            padding: 12px;
            border: 1px solid #555;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            line-height: 1.5;
            resize: vertical;
            background: #1e1e1e;
            color: #e0e0e0;
        }
        
        textarea:focus {
            outline: none;
            border-color: #4a9eff;
            box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2);
        }
        
        .buttons {
            display: flex;
            gap: 10px;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        
        .btn-primary {
            background: #4a9eff;
            color: white;
        }
        
        .btn-primary:hover {
            background: #357abd;
        }
        
        .btn-secondary {
            background: #555;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #666;
        }
        
        .status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 4px;
            display: none;
        }
        
        .status.success {
            background: #1e4d2b;
            color: #4ade80;
            border: 1px solid #22c55e;
        }
        
        .status.error {
            background: #4d1e1e;
            color: #f87171;
            border: 1px solid #ef4444;
        }
        
        .bot-info {
            background: #1e1e1e;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 14px;
            color: #b0b0b0;
        }
        
        .call-ui {
            margin-bottom: 20px;
            padding: 20px;
            background: #1e1e1e;
            border-radius: 8px;
            border: 1px solid #404040;
        }
        
        .call-ui h2 {
            color: #ffffff;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .call-ui .form-group {
            margin-bottom: 20px;
        }
        
        .call-ui label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #b0b0b0;
            font-size: 14px;
        }
        
        .call-ui input, .call-ui select {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #555;
            border-radius: 6px;
            background: #1e1e1e;
            color: #e0e0e0;
            font-size: 14px;
            box-sizing: border-box;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        
        .call-ui input:focus, .call-ui select:focus {
            outline: none;
            border-color: #4a9eff;
            box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2);
        }
        
        .call-ui .btn-call {
            width: 100%;
            padding: 14px 20px;
            background: #22c55e;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .call-ui .btn-call:hover {
            background: #16a34a;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
        }
        
        .call-ui .btn-call:disabled {
            background: #555;
            cursor: not-allowed;
        }
        
        .call-results {
            margin-top: 20px;
            padding: 20px;
            background: #1e1e1e;
            border-radius: 8px;
            border: 1px solid #404040;
        }
        
        .call-results h3 {
            color: #ffffff;
            margin-bottom: 15px;
            font-size: 16px;
            font-weight: 500;
        }
        
        .call-item {
            background: #2d2d2d;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 10px;
            border: 1px solid #404040;
        }
        
        .call-item:last-child {
            margin-bottom: 0;
        }
        
        .call-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .call-sid {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            color: #4a9eff;
            background: rgba(74, 158, 255, 0.1);
            padding: 4px 8px;
            border-radius: 4px;
        }
        
        .call-status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .call-status.completed {
            background: #1e4d2b;
            color: #4ade80;
        }
        
        .call-status.in-progress {
            background: #1e3a4d;
            color: #4a9eff;
        }
        
        .call-status.ringing {
            background: #4d3e1e;
            color: #fbbf24;
        }
        
        .call-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .call-detail {
            display: flex;
            flex-direction: column;
        }
        
        .call-detail-label {
            font-size: 12px;
            color: #b0b0b0;
            margin-bottom: 4px;
        }
        
        .call-detail-value {
            font-size: 14px;
            color: #ffffff;
            font-weight: 500;
        }
        
        .call-transcript {
            background: #1a1a1a;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
            font-size: 13px;
            line-height: 1.4;
            color: #e0e0e0;
            max-height: 100px;
            overflow-y: auto;
        }
        
        .call-audio {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .audio-player {
            flex: 1;
            height: 32px;
        }
        
        .download-btn {
            padding: 6px 12px;
            background: #4a9eff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            text-decoration: none;
            display: inline-block;
        }
        
        .download-btn:hover {
            background: #357abd;
        }
        
        .polling-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #4a9eff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .main-container {
                flex-direction: column;
            }
            
            .left-panel {
                flex: none;
                margin-bottom: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="left-panel">
            <div class="call-ui">
                <h2>Make a Call</h2>
                <form id="callForm">
                    <div class="form-group">
                        <label for="customerName">Customer Name:</label>
                        <input 
                            type="text" 
                            id="customerName" 
                            placeholder="Enter customer name"
                            value="there"
                        >
                    </div>
                    
                    <div class="form-group">
                        <label for="phoneNumber">Phone Number:</label>
                        <input 
                            type="tel" 
                            id="phoneNumber" 
                            placeholder="Enter phone number"
                            value="+91"
                        >
                    </div>
                    
                    <div class="form-group">
                        <label for="botType">Bot Type (Controls Both Call & Prompt):</label>
                        <select id="botType">
                            <option value="multimodel">Multimodel Bot</option>
                            <option value="standard">Standard Bot</option>
                        </select>
                    </div>
                    
                    <button type="submit" class="btn-call" id="callBtn">
                        Make Call
                    </button>
                </form>
            </div>
            
            <div class="call-results">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3>Current Call</h3>
                    <button id="clearCallBtn" class="btn-secondary" style="padding: 6px 12px; font-size: 12px; display: none;">
                        Clear Call
                    </button>
                </div>
                <div id="callResultsList">
                    <div style="text-align: center; color: #b0b0b0; padding: 20px;">
                        No active call
                    </div>
                </div>
            </div>
        </div>
        
        <div class="right-panel">
            <h1>Prompt Editor</h1>
            <div style="text-align: center; margin-bottom: 20px; color: #b0b0b0; font-size: 14px;">
                Bot type is controlled by the dropdown in the call section
            </div>
            
            <div class="tabs">
                <button class="tab active" data-tab="multimodel">Multimodel Bot</button>
                <button class="tab" data-tab="standard">Standard Bot</button>
            </div>
        
        <div id="multimodel-tab" class="tab-content active">
            <div class="bot-info">
                <strong>Multimodel Bot:</strong> Advanced bot with multiple AI models for enhanced conversation capabilities.
            </div>
            <form id="multimodelForm">
            <div class="form-group">
                    <label for="multimodelPromptText">Raw Prompt:</label>
                <textarea 
                        id="multimodelPromptText" 
                    placeholder="Enter your prompt here..."
                    required
                ></textarea>
            </div>
            
            <div class="buttons">
                    <button type="submit" class="btn-primary" id="multimodelSaveBtn">Save Prompt</button>
                    <button type="button" class="btn-secondary" id="multimodelResetBtn">Reset</button>
                </div>
            </form>
        </div>
        
        <div id="standard-tab" class="tab-content">
            <div class="bot-info">
                <strong>Standard Bot:</strong> Standard bot with single AI model for basic conversation capabilities.
            </div>
            <form id="standardForm">
                <div class="form-group">
                    <label for="standardPromptText">Raw Prompt:</label>
                    <textarea 
                        id="standardPromptText" 
                        placeholder="Enter your prompt here..."
                        required
                    ></textarea>
                </div>
                
                <div class="buttons">
                    <button type="submit" class="btn-primary" id="standardSaveBtn">Save Prompt</button>
                    <button type="button" class="btn-secondary" id="standardResetBtn">Reset</button>
            </div>
        </form>
        </div>
        
        <div class="status" id="statusMessage"></div>
        </div>
    </div>

    <script>
        let originalPrompts = {
            multimodel: '',
            standard: ''
        };
        
        let currentTab = 'multimodel';
        
        // Tab switching functionality
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                switchTab(tabName);
            });
        });
        
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            currentTab = tabName;
            
            // Update call dropdown to match the selected tab
            const botTypeSelect = document.getElementById('botType');
            if (botTypeSelect) {
                botTypeSelect.value = tabName;
            }
        }
        
        // Bot type dropdown change handler
        function onBotTypeChange() {
            const botType = document.getElementById('botType').value;
            switchTab(botType);
        }
        
        async function loadCurrentPrompt(botType) {
            try {
                const response = await fetch(`/api/get-raw-prompt?multimodel=${botType === 'multimodel'}`);
                if (response.ok) {
                    const data = await response.json();
                    originalPrompts[botType] = data.prompt || '';
                    document.getElementById(`${botType}PromptText`).value = originalPrompts[botType];
                }
            } catch (error) {
                console.error(`Error loading ${botType} prompt:`, error);
            }
        }
        
        async function savePrompt(prompt, botType) {
            try {
                const response = await fetch('/api/save-prompt', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        prompt: prompt,
                        multimodel: botType === 'multimodel'
                    })
                });
                
                if (response.ok) {
                    showMessage(`${botType.charAt(0).toUpperCase() + botType.slice(1)} bot prompt saved successfully!`, 'success');
                    originalPrompts[botType] = prompt;
                } else {
                    const errorData = await response.json();
                    showMessage(`Failed to save: ${errorData.detail || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                showMessage('Error saving prompt', 'error');
            }
        }
        
        function showMessage(message, type) {
            const statusDiv = document.getElementById('statusMessage');
            statusDiv.textContent = message;
            statusDiv.className = `status ${type}`;
            statusDiv.style.display = 'block';
            
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 3000);
        }
        
        // Form event listeners
        document.getElementById('multimodelForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = document.getElementById('multimodelPromptText').value.trim();
            if (promptText) {
                await savePrompt(promptText, 'multimodel');
            }
        });
        
        document.getElementById('standardForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = document.getElementById('standardPromptText').value.trim();
            if (promptText) {
                await savePrompt(promptText, 'standard');
            }
        });
        
        // Generic save function that works with current tab
        function saveCurrentPrompt() {
            const currentPromptText = document.getElementById(`${currentTab}PromptText`).value.trim();
            if (currentPromptText) {
                savePrompt(currentPromptText, currentTab);
            }
        }
        
        document.getElementById('multimodelResetBtn').addEventListener('click', () => {
            document.getElementById('multimodelPromptText').value = originalPrompts.multimodel;
            showMessage('Reset to original', 'success');
        });
        
        document.getElementById('standardResetBtn').addEventListener('click', () => {
            document.getElementById('standardPromptText').value = originalPrompts.standard;
            showMessage('Reset to original', 'success');
        });
        
        // Generic reset function that works with current tab
        function resetCurrentPrompt() {
            document.getElementById(`${currentTab}PromptText`).value = originalPrompts[currentTab];
            showMessage('Reset to original', 'success');
        }
        
        // Call results management
        let currentCall = null;
        let pollingInterval = null;
        let callCompletedTime = null;
        
        function setCurrentCall(callData) {
            currentCall = callData;
            updateCallResultsDisplay();
            // Show clear button when there's a call
            document.getElementById('clearCallBtn').style.display = 'inline-block';
        }
        
        function updateCurrentCall(updatedData) {
            if (currentCall) {
                currentCall = { ...currentCall, ...updatedData };
                updateCallResultsDisplay();
            }
        }
        
        function clearCurrentCall() {
            currentCall = null;
            callCompletedTime = null;
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
            updateCallResultsDisplay();
            // Hide clear button when no call
            document.getElementById('clearCallBtn').style.display = 'none';
        }
        
        function updateCallResultsDisplay() {
            const container = document.getElementById('callResultsList');
            
            if (!currentCall) {
                container.innerHTML = '<div style="text-align: center; color: #b0b0b0; padding: 20px;">No active call</div>';
                return;
            }
            
            container.innerHTML = `
                <div class="call-item">
                    <div class="call-header">
                        <span class="call-sid">${currentCall.call_sid}</span>
                        <span class="call-status ${currentCall.status}">
                            ${currentCall.status === 'completed' ? 
                              (callCompletedTime && (Date.now() - callCompletedTime) < 60000 ? 
                                '✅ Completed (Generating Recording...)' : '✅ Completed') : 
                              currentCall.status === 'in-progress' ? '🔄 In Progress' : 
                              currentCall.status === 'ringing' ? '📞 Ringing' : currentCall.status}
                        </span>
                    </div>
                    
                    <div class="call-details">
                        <div class="call-detail">
                            <div class="call-detail-label">Phone</div>
                            <div class="call-detail-value">${currentCall.phone_number}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Name</div>
                            <div class="call-detail-value">${currentCall.name || 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Bot Type</div>
                            <div class="call-detail-value">${currentCall.multimodel ? 'Multimodel' : 'Standard'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Duration</div>
                            <div class="call-detail-value">${currentCall.call_duration ? currentCall.call_duration + 's' : 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Cost</div>
                            <div class="call-detail-value">${currentCall.call_cost ? '$' + currentCall.call_cost.toFixed(4) : 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Created</div>
                            <div class="call-detail-value">${currentCall.created_at ? new Date(currentCall.created_at).toLocaleString() : 'N/A'}</div>
                        </div>
                    </div>
                    
                    ${currentCall.transcript ? `
                        <div class="call-transcript">
                            <strong>Transcript:</strong><br>
                            ${currentCall.transcript}
                        </div>
                    ` : ''}
                    
                    ${currentCall.recording_url ? `
                        <div class="call-audio">
                            <audio controls class="audio-player">
                                <source src="${currentCall.recording_url}" type="audio/wav">
                                Your browser does not support the audio element.
                            </audio>
                            <a href="${currentCall.recording_url}" download class="download-btn">Download</a>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        async function pollCallStatus(callSid) {
            try {
                const response = await fetch(`/api/call-details/${callSid}`);
                if (response.ok) {
                    const callData = await response.json();
                    updateCurrentCall(callData);
                    
                    console.log(`Polling call ${callSid}, status: ${callData.status}`);
                    
                    // Check if call just completed
                    if (['completed', 'failed', 'busy', 'no-answer', 'canceled'].includes(callData.status)) {
                        if (!callCompletedTime) {
                            callCompletedTime = Date.now();
                            console.log('Call completed, continuing to poll for 1 minute for recording generation...');
                        }
                        
                        // Stop polling after 1 minute (60 seconds) from completion
                        const timeSinceCompletion = Date.now() - callCompletedTime;
                        const remainingTime = Math.max(0, 60000 - timeSinceCompletion);
                        console.log(`Time since completion: ${Math.round(timeSinceCompletion/1000)}s, remaining: ${Math.round(remainingTime/1000)}s`);
                        
                        if (timeSinceCompletion >= 60000) { // 60 seconds = 60000ms
                            if (pollingInterval) {
                                clearInterval(pollingInterval);
                                pollingInterval = null;
                                console.log('Stopped polling after 1 minute post-completion');
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('Error polling call status:', error);
            }
        }
        
        function startPolling(callSid) {
            // Clear any existing polling
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
            
            // Reset completion time for new call
            callCompletedTime = null;
            
            // Poll immediately
            pollCallStatus(callSid);
            
            // Then poll every 3 seconds
            pollingInterval = setInterval(() => pollCallStatus(callSid), 3000);
        }
        
        // Call form functionality
        async function makeCall(callData) {
            try {
                const response = await fetch('/outbound', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(callData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    showMessage(`Call initiated successfully! Call SID: ${result.call_sid}`, 'success');
                    
                    // Set current call and start polling
                    setCurrentCall({
                        call_sid: result.call_sid,
                        phone_number: callData.phone_number,
                        name: callData.name,
                        multimodel: callData.multimodel,
                        status: 'ringing',
                        created_at: new Date().toISOString()
                    });
                    
                    startPolling(result.call_sid);
                    
                    // Disable the button temporarily
                    document.getElementById('callBtn').disabled = true;
                    document.getElementById('callBtn').textContent = 'Call Initiated...';
                    
                    // Re-enable after 5 seconds
                    setTimeout(() => {
                        document.getElementById('callBtn').disabled = false;
                        document.getElementById('callBtn').textContent = 'Make Call';
                    }, 5000);
                } else {
                    const errorData = await response.json();
                    showMessage(`Failed to initiate call: ${errorData.detail || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                showMessage('Error initiating call', 'error');
            }
        }
        
        // Call form event listener
        document.getElementById('callForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const customerName = document.getElementById('customerName').value.trim();
            const phoneNumber = document.getElementById('phoneNumber').value.trim();
            const botType = document.getElementById('botType').value;
            
            if (!phoneNumber) {
                showMessage('Please enter a phone number', 'error');
                return;
            }
            
            const callData = {
                phone_number: phoneNumber,
                name: customerName || 'there',
                multimodel: botType === 'multimodel'
            };
            
            await makeCall(callData);
        });
        
        // Clear call button event listener
        document.getElementById('clearCallBtn').addEventListener('click', () => {
            clearCurrentCall();
            showMessage('Call cleared', 'success');
        });
        
        // Force stop polling function for testing
        function forceStopPolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
                console.log('Force stopped polling');
            }
        }
        
        // Make it available globally for testing
        window.forceStopPolling = forceStopPolling;
        
        // Cleanup polling interval on page unload
        window.addEventListener('beforeunload', () => {
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
        });
        
        // Bot type dropdown event listener
        document.getElementById('botType').addEventListener('change', onBotTypeChange);
        
        // Load prompts on page load
        document.addEventListener('DOMContentLoaded', () => {
            loadCurrentPrompt('multimodel');
            loadCurrentPrompt('standard');
        });
    </script>
</body>
</html>
"""
