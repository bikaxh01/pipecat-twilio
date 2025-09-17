def create_prompt_ui():
    """Create a simple HTML UI for editing the raw prompt"""
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
        
        .container {
            max-width: 800px;
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
            font-size: 24px;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Prompt Editor</h1>
        
        <form id="promptForm">
            <div class="form-group">
                <label for="promptText">Raw Prompt:</label>
                <textarea 
                    id="promptText" 
                    placeholder="Enter your prompt here..."
                    required
                ></textarea>
            </div>
            
            <div class="buttons">
                <button type="submit" class="btn-primary" id="saveBtn">Save Prompt</button>
                <button type="button" class="btn-secondary" id="resetBtn">Reset</button>
            </div>
        </form>
        
        <div class="status" id="statusMessage"></div>
    </div>

    <script>
        let originalPrompt = '';
        
        async function loadCurrentPrompt() {
            try {
                const response = await fetch('/api/get-raw-prompt');
                if (response.ok) {
                    const data = await response.json();
                    originalPrompt = data.prompt || '';
                    document.getElementById('promptText').value = originalPrompt;
                }
            } catch (error) {
                console.error('Error loading prompt:', error);
            }
        }
        
        async function savePrompt(prompt) {
            try {
                const response = await fetch('/api/save-prompt', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ prompt: prompt })
                });
                
                if (response.ok) {
                    showMessage('Prompt saved successfully!', 'success');
                    originalPrompt = prompt;
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
        
        document.getElementById('promptForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const promptText = document.getElementById('promptText').value.trim();
            if (promptText) {
                await savePrompt(promptText);
            }
        });
        
        document.getElementById('resetBtn').addEventListener('click', () => {
            document.getElementById('promptText').value = originalPrompt;
            showMessage('Reset to original', 'success');
        });
        
        document.addEventListener('DOMContentLoaded', loadCurrentPrompt);
    </script>
</body>
</html>
"""
