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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%);
            margin: 0;
            padding: 24px;
            color: #ffffff;
            min-height: 100vh;
        }
        
        .main-container {
            display: grid;
            grid-template-columns: 350px 1fr 350px;
            gap: 24px;
            max-width: 1800px;
            margin: 0 auto;
            min-height: calc(100vh - 48px);
        }
        
        .left-panel {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            height: fit-content;
        }
        
        .middle-panel {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            height: fit-content;
        }
        
        .right-panel {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            height: fit-content;
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
            margin-bottom: 32px;
            font-size: 32px;
            text-align: center;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 0%, #a0a0a0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        h2 {
            color: #ffffff;
            margin-bottom: 20px;
            font-size: 22px;
            font-weight: 600;
            letter-spacing: -0.3px;
        }
        
        h3 {
            color: #ffffff;
            margin-bottom: 16px;
            font-size: 18px;
            font-weight: 600;
            letter-spacing: -0.2px;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 32px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 4px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .tab {
            flex: 1;
            padding: 12px 20px;
            cursor: pointer;
            border: none;
            background: none;
            color: #a0a0a0;
            font-size: 15px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-radius: 8px;
            font-weight: 500;
            letter-spacing: -0.1px;
        }
        
        .tab.active {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        
        .tab:hover:not(.active) {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.08);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #ffffff;
            font-size: 14px;
            letter-spacing: -0.1px;
        }
        
        textarea {
            width: 100%;
            height: 300px;
            padding: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            line-height: 1.6;
            resize: vertical;
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-sizing: border-box;
        }
        
        textarea:focus {
            outline: none;
            border-color: rgba(74, 158, 255, 0.5);
            box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
            background: rgba(255, 255, 255, 0.08);
        }
        
        .buttons {
            display: flex;
            gap: 12px;
        }
        
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            letter-spacing: -0.1px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #4a9eff 0%, #357abd 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(74, 158, 255, 0.3);
        }
        
        .btn-primary:hover {
            background: linear-gradient(135deg, #357abd 0%, #2c5aa0 100%);
            box-shadow: 0 6px 16px rgba(74, 158, 255, 0.4);
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }
        
        .status {
            margin-top: 20px;
            padding: 16px;
            border-radius: 12px;
            display: none;
            font-weight: 500;
        }
        
        .status.success {
            background: rgba(34, 197, 94, 0.1);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        
        .status.error {
            background: rgba(239, 68, 68, 0.1);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .bot-info {
            background: rgba(255, 255, 255, 0.05);
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #a0a0a0;
            border: 1px solid rgba(255, 255, 255, 0.1);
            line-height: 1.5;
        }
        
        .call-ui {
            margin-bottom: 24px;
            padding: 24px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .call-ui h2 {
            color: #ffffff;
            margin-bottom: 20px;
            font-size: 20px;
            font-weight: 600;
        }
        
        .call-ui .form-group {
            margin-bottom: 20px;
        }
        
        .call-ui label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #ffffff;
            font-size: 14px;
        }
        
        .call-ui input {
            width: 100%;
            padding: 14px 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
            font-size: 14px;
            box-sizing: border-box;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .call-ui input:focus {
            outline: none;
            border-color: rgba(74, 158, 255, 0.5);
            box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
            background: rgba(255, 255, 255, 0.08);
        }
        
        /* Clean modern dropdown styling */
        .call-ui select {
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
            width: 100%;
            padding: 14px 16px;
            padding-right: 44px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
            color: #ffffff;
            font-size: 14px;
            font-weight: 500;
            box-sizing: border-box;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6,9 12,15 18,9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 16px center;
            background-size: 16px;
            cursor: pointer;
        }
        
        .call-ui select:focus {
            outline: none;
            border-color: rgba(59, 130, 246, 0.6);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.08) 100%);
        }
        
        .call-ui select:hover {
            border-color: rgba(255, 255, 255, 0.3);
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.08) 100%);
        }
        
        /* Modern dropdown option styling */
        .call-ui select option {
            background: #1e1e1e !important;
            color: #ffffff !important;
            padding: 12px 16px !important;
            font-size: 14px !important;
            font-weight: 400 !important;
            border: none !important;
            margin: 0 !important;
        }
        
        .call-ui select option:checked,
        .call-ui select option:selected {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            font-weight: 500 !important;
        }
        
        .call-ui select option:hover {
            background: linear-gradient(135deg, #374151 0%, #4b5563 100%) !important;
            color: #ffffff !important;
        }
        
        /* General select styling for consistency */
        select {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }
        
        /* Modern option styling */
        select option {
            background: #1e1e1e !important;
            color: #ffffff !important;
            padding: 12px 16px !important;
            font-size: 14px !important;
            border: none !important;
        }
        
        select option:checked,
        select option:selected {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            font-weight: 500 !important;
        }
        
        select option:hover {
            background: linear-gradient(135deg, #374151 0%, #4b5563 100%) !important;
            color: #ffffff !important;
        }
        
        .provider-dropdowns {
            display: none !important;
        }
        
        .provider-dropdowns.show {
            display: none !important;
        }
        
        .call-ui .btn-call {
            width: 100%;
            padding: 16px 24px;
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 700;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
        }
        
        .call-ui .btn-call:hover {
            background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(34, 197, 94, 0.4);
        }
        
        .call-ui .btn-call:disabled {
            background: rgba(255, 255, 255, 0.1);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .call-results {
            margin-top: 24px;
            padding: 24px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .call-results h3 {
            color: #ffffff;
            margin-bottom: 20px;
            font-size: 18px;
            font-weight: 600;
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
        }
        
        .call-transcript textarea {
            width: 100%;
            min-height: 80px;
            max-height: 200px;
            padding: 8px;
            border: 1px solid #555;
            border-radius: 4px;
            background: #1a1a1a;
            color: #e0e0e0;
            font-size: 13px;
            line-height: 1.4;
            font-family: inherit;
            resize: vertical;
            box-sizing: border-box;
        }
        
        .call-transcript textarea:focus {
            outline: none;
            border-color: #4a9eff;
            box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2);
        }
        
        .transcript-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .copy-transcript-btn {
            padding: 4px 8px;
            background: #4a9eff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .copy-transcript-btn:hover {
            background: #357abd;
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
        
        /* Dialog Styles */
        .dialog-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .dialog-content {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 900px;
            width: 90%;
            max-height: 85vh;
            overflow-y: auto;
        }
        
        .dialog-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .dialog-header h2 {
            margin: 0;
            color: #ffffff;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }
        
        .dialog-close-btn {
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #a0a0a0;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .dialog-close-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            color: #ffffff;
            transform: scale(1.05);
        }
        
        .dialog-body {
            padding: 24px;
        }
        
        .call-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .call-card:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(74, 158, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
        }
        
        .call-card:last-child {
            margin-bottom: 0;
        }
        
        .call-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .call-card-phone {
            font-size: 16px;
            color: #ffffff;
            font-weight: 600;
            letter-spacing: -0.2px;
        }
        
        .call-card-status {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.3px;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 4px;
            min-width: 70px;
            justify-content: center;
            backdrop-filter: blur(10px);
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
            transition: all 0.2s ease;
        }
        
        .call-card-status.completed {
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.25), rgba(34, 197, 94, 0.15));
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.4);
            box-shadow: 0 2px 8px rgba(34, 197, 94, 0.2);
        }
        
        .call-card-status.in-progress {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(59, 130, 246, 0.15));
            color: #3b82f6;
            border: 1px solid rgba(59, 130, 246, 0.4);
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
        }
        
        .call-card-status.ringing {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.25), rgba(245, 158, 11, 0.15));
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.4);
            box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
        }
        
        .call-card-status.failed {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.25), rgba(239, 68, 68, 0.15));
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.4);
            box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);
        }
        
        .call-card-status.busy {
            background: linear-gradient(135deg, rgba(107, 114, 128, 0.25), rgba(107, 114, 128, 0.15));
            color: #6b7280;
            border: 1px solid rgba(107, 114, 128, 0.4);
            box-shadow: 0 2px 8px rgba(107, 114, 128, 0.2);
        }
        
        .call-card-status.no-answer {
            background: linear-gradient(135deg, rgba(156, 163, 175, 0.25), rgba(156, 163, 175, 0.15));
            color: #9ca3af;
            border: 1px solid rgba(156, 163, 175, 0.4);
            box-shadow: 0 2px 8px rgba(156, 163, 175, 0.2);
        }
        
        .call-card-status:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        .call-card-sid {
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 11px;
            color: #a0a0a0;
            background: rgba(74, 158, 255, 0.1);
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(74, 158, 255, 0.2);
        }
        
        @media (max-width: 1200px) {
            .main-container {
                grid-template-columns: 1fr;
                gap: 16px;
            }
        }
        
        @media (max-width: 768px) {
            body {
                padding: 16px;
            }
            
            .main-container {
                grid-template-columns: 1fr;
                gap: 16px;
            }
            
            .dialog-content {
                width: 95%;
                margin: 16px;
                border-radius: 16px;
            }
            
            .call-ui .btn-call {
                font-size: 14px;
                padding: 14px 20px;
            }
            
            .tabs {
                margin-bottom: 24px;
            }
            
            .tab {
                padding: 10px 16px;
                font-size: 14px;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Left Panel: Call Configuration -->
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
                            <option value="standard" selected>Standard Bot</option>
                        </select>
                    </div>
                    
                    <div class="provider-dropdowns" id="providerDropdowns">
                        <div class="form-group">
                            <label for="ttsProvider">TTS Provider:</label>
                            <select id="ttsProvider">
                                <option value="sarvam_ai" selected>Sarvam AI</option>
                                <option value="cartesia">Cartesia</option>
                                <option value="elevenlabs">ElevenLabs</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="sttProvider">STT Provider:</label>
                            <select id="sttProvider">
                                <option value="deepgram" selected>Deepgram</option>
                                <option value="gladia">Gladia</option>
                                <option value="soniox">SonioX</option>
                                <option value="cartesia">Cartesia</option>
                                <option value="groq">Groq</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="llmProvider">LLM Provider:</label>
                            <select id="llmProvider">
                                <option value="openai/gpt-4o-mini-2024-07-18" selected>OpenAI GPT-4o Mini (2024-07-18)</option>
                                <option value="gemini/gemini-2.5-pro">Gemini 2.5 Pro</option>
                                <option value="gemini/gemini-2.5-flash">Gemini 2.5 Flash</option>
                                <option value="gemini/gemini-2.5-flash-lite">Gemini 2.5 Flash Lite</option>
                                <option value="gemini/gemini-2.0-flash">Gemini 2.0 Flash</option>
                                <option value="gemini/gemini-2.0-flash-lite">Gemini 2.0 Flash Lite</option>
                                <option value="openai/gpt-5-2025-08-07">OpenAI GPT-5 (2025-08-07)</option>
                                <option value="openai/gpt-5-mini-2025-08-07">OpenAI GPT-5 Mini (2025-08-07)</option>
                                <option value="openai/gpt-5-nano-2025-08-07">OpenAI GPT-5 Nano (2025-08-07)</option>
                                <option value="openai/gpt-4.1-2025-04-14">OpenAI GPT-4.1 (2025-04-14)</option>
                                <option value="openai/gpt-4.1-nano-2025-04-14">OpenAI GPT-4.1 Nano (2025-04-14)</option>
                                <option value="openai/o4-mini-2025-04-16">OpenAI O4 Mini (2025-04-16)</option>
                                <option value="openai/gpt-4.1-mini-2025-04-14">OpenAI GPT-4.1 Mini (2025-04-14)</option>
                            </select>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn-call" id="callBtn">
                        Make Call
                    </button>
                </form>
            </div>
        </div>
        
        <!-- Middle Panel: Prompt Editor -->
        <div class="middle-panel">
            <h1>Prompt Editor</h1>
            <div style="text-align: center; margin-bottom: 20px; color: #a0a0a0; font-size: 14px;">
                Bot type is controlled by the dropdown in the call section
            </div>
            
            <div class="tabs">
                <button class="tab" data-tab="multimodel">Multimodel Bot</button>
                <button class="tab active" data-tab="standard">Standard Bot</button>
            </div>
        
            <div id="multimodel-tab" class="tab-content">
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
            
            <div id="standard-tab" class="tab-content active">
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
        
        <!-- Right Panel: Call List -->
        <div class="right-panel">
            <div class="call-results">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>Latest Calls</h3>
                    <button id="refreshCallsBtn" class="btn-secondary" style="padding: 8px 16px; font-size: 12px;">
                        Refresh
                    </button>
                </div>
                <div id="callResultsList">
                    <div style="text-align: center; color: #a0a0a0; padding: 20px;">
                        Loading calls...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Call Details Dialog -->
    <div id="callDetailsDialog" class="dialog-overlay" style="display: none;">
        <div class="dialog-content">
            <div class="dialog-header">
                <h2>Call Details</h2>
                <button id="closeDialogBtn" class="dialog-close-btn">&times;</button>
            </div>
            <div class="dialog-body" id="dialogBody">
                <!-- Call details will be populated here -->
            </div>
        </div>
    </div>

    <script>
        let originalPrompts = {
            multimodel: '',
            standard: ''
        };
        
        let currentTab = 'standard';
        
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
            
            // Show/hide provider dropdowns based on bot type
            const providerDropdowns = document.getElementById('providerDropdowns');
            if (providerDropdowns) {
                if (tabName === 'standard') {
                    providerDropdowns.classList.add('show');
                } else {
                    providerDropdowns.classList.remove('show');
                }
            }
        }
        
        // Bot type dropdown change handler
        function onBotTypeChange() {
            const botType = document.getElementById('botType').value;
            const providerDropdowns = document.getElementById('providerDropdowns');
            
            // Show/hide provider dropdowns based on bot type
            if (botType === 'standard') {
                providerDropdowns.classList.add('show');
            } else {
                providerDropdowns.classList.remove('show');
            }
            
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
        
        // Latest calls management
        let latestCalls = [];
        let currentCall = null;
        let pollingInterval = null;
        let callCompletedTime = null;
        
        async function loadLatestCalls() {
            try {
                const response = await fetch('/api/latest-calls');
                if (response.ok) {
                    const data = await response.json();
                    latestCalls = data.calls || [];
                    updateCallResultsDisplay();
                } else {
                    console.error('Failed to load latest calls');
                    updateCallResultsDisplay();
                }
            } catch (error) {
                console.error('Error loading latest calls:', error);
                updateCallResultsDisplay();
            }
        }
        
        function setCurrentCall(callData) {
            currentCall = callData;
            // Refresh latest calls when a new call is made
            loadLatestCalls();
        }
        
        function updateCurrentCall(updatedData) {
            if (currentCall) {
                currentCall = { ...currentCall, ...updatedData };
                // Refresh latest calls when current call is updated
                loadLatestCalls();
            }
        }
        
        function clearCurrentCall() {
            currentCall = null;
            callCompletedTime = null;
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
            // Refresh latest calls
            loadLatestCalls();
        }
        
        function updateCallResultsDisplay() {
            const container = document.getElementById('callResultsList');
            
            if (latestCalls.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #b0b0b0; padding: 20px;">No calls found</div>';
                return;
            }
            
            let html = '';
            latestCalls.forEach(call => {
                html += `
                    <div class="call-card" onclick="openCallDetails('${call.call_sid}')">
                        <div class="call-card-header">
                            <div class="call-card-phone">${call.phone_number}</div>
                            <span class="call-card-status ${call.status}">
                                ${call.status === 'completed' ? '✓ COMPLETED' : 
                                  call.status === 'in-progress' ? '⟳ IN PROGRESS' : 
                                  call.status === 'ringing' ? '📞 RINGING' : 
                                  call.status === 'failed' ? '✗ FAILED' : 
                                  call.status === 'busy' ? '📵 BUSY' : 
                                  call.status === 'no-answer' ? '📵 NO ANSWER' : 
                                  call.status.toUpperCase()}
                        </span>
                    </div>
                        <div class="call-card-sid">${call.call_sid}</div>
                        ${call.metrics || call.cost ? `
                            <div style="margin-top: 8px; display: flex; gap: 12px; font-size: 11px;">
                                ${call.metrics ? `
                                    <div style="color: #4ade80; font-weight: 600;">
                                        ⚡ ${call.metrics.total_latency_ms ? call.metrics.total_latency_ms.toFixed(0) + 'ms' : 
                                          (call.metrics.tts_ttfb_ms && call.metrics.stt_ttfb_ms && call.metrics.llm_ttfb_ms) ? 
                                          (call.metrics.tts_ttfb_ms + call.metrics.stt_ttfb_ms + call.metrics.llm_ttfb_ms).toFixed(0) + 'ms' : 'N/A'}
                                    </div>
                                ` : ''}
                                ${call.cost ? `
                                    <div style="color: #fbbf24; font-weight: 600;">
                                        💰 ${call.cost.total_cost ? '$' + call.cost.total_cost.toFixed(3) : 
                                          (call.cost.llm_cost && call.cost.tts_cost && call.cost.stt_cost) ? 
                                          '$' + (call.cost.llm_cost + call.cost.tts_cost + call.cost.stt_cost).toFixed(3) : 'N/A'}
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}
                </div>
            `;
            });
            
            container.innerHTML = html;
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
                    const callInfo = {
                        call_sid: result.call_sid,
                        phone_number: callData.phone_number,
                        name: callData.name,
                        multimodel: callData.multimodel,
                        status: 'ringing',
                        created_at: new Date().toISOString()
                    };
                    
                    // Only include provider data if available (for standard bot)
                    if (callData.tts_provider) callInfo.tts_provider = callData.tts_provider;
                    if (callData.stt_provider) callInfo.stt_provider = callData.stt_provider;
                    if (callData.llm_provider) callInfo.llm_provider = callData.llm_provider;
                    
                    setCurrentCall(callInfo);
                    
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
            
            // Only include provider data for standard bot
            if (botType === 'standard') {
                const ttsProvider = document.getElementById('ttsProvider').value;
                const sttProvider = document.getElementById('sttProvider').value;
                const llmProvider = document.getElementById('llmProvider').value;
                
                callData.tts_provider = ttsProvider;
                callData.stt_provider = sttProvider;
                callData.llm_provider = llmProvider;
            }
            
            await makeCall(callData);
        });
        
        // Refresh calls button event listener
        document.getElementById('refreshCallsBtn').addEventListener('click', () => {
            loadLatestCalls();
            showMessage('Calls refreshed', 'success');
        });
        
        // Dialog functionality
        async function openCallDetails(callSid) {
            try {
                const response = await fetch(`/api/call-details/${callSid}`);
                if (response.ok) {
                    const callData = await response.json();
                    showCallDetailsDialog(callData);
                } else {
                    showMessage('Failed to load call details', 'error');
                }
            } catch (error) {
                showMessage('Error loading call details', 'error');
            }
        }
        
        function showCallDetailsDialog(callData) {
            const dialog = document.getElementById('callDetailsDialog');
            const dialogBody = document.getElementById('dialogBody');
            
            dialogBody.innerHTML = `
                <div class="call-item">
                    <div class="call-header">
                        <span class="call-sid">${callData.call_sid}</span>
                        <span class="call-status ${callData.status}">
                            ${callData.status === 'completed' ? '✅ Completed' : 
                              callData.status === 'in-progress' ? '🔄 In Progress' : 
                              callData.status === 'ringing' ? '📞 Ringing' : callData.status}
                        </span>
                    </div>
                    
                    <div class="call-details">
                        <div class="call-detail">
                            <div class="call-detail-label">Phone</div>
                            <div class="call-detail-value">${callData.phone_number}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Name</div>
                            <div class="call-detail-value">${callData.name || 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Bot Type</div>
                            <div class="call-detail-value">${callData.multimodel ? 'Multimodel' : 'Standard'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">TTS Provider</div>
                            <div class="call-detail-value">${callData.tts_provider || 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">STT Provider</div>
                            <div class="call-detail-value">${callData.stt_provider || 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">LLM Provider</div>
                            <div class="call-detail-value">${callData.llm_provider || 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Duration</div>
                            <div class="call-detail-value">${callData.call_duration ? callData.call_duration + 's' : 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Cost</div>
                            <div class="call-detail-value">${callData.call_cost ? '$' + callData.call_cost.toFixed(4) : 'N/A'}</div>
                        </div>
                        <div class="call-detail">
                            <div class="call-detail-label">Created</div>
                            <div class="call-detail-value">${callData.created_at ? new Date(callData.created_at).toLocaleString() : 'N/A'}</div>
                        </div>
                    </div>
                    
                    ${callData.metrics ? `
                        <div style="margin-top: 20px;">
                            <h4 style="color: #ffffff; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Performance Metrics</h4>
                            <div class="call-details" style="grid-template-columns: 1fr 1fr 1fr;">
                                <div class="call-detail">
                                    <div class="call-detail-label">TTS TTFB</div>
                                    <div class="call-detail-value">${callData.metrics.tts_ttfb_ms ? callData.metrics.tts_ttfb_ms.toFixed(2) + 'ms' : 'N/A'}</div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">STT TTFB</div>
                                    <div class="call-detail-value">${callData.metrics.stt_ttfb_ms ? callData.metrics.stt_ttfb_ms.toFixed(2) + 'ms' : 'N/A'}</div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">LLM TTFB</div>
                                    <div class="call-detail-value">${callData.metrics.llm_ttfb_ms ? callData.metrics.llm_ttfb_ms.toFixed(2) + 'ms' : 'N/A'}</div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">Total Latency</div>
                                    <div class="call-detail-value" style="color: #4ade80; font-weight: 700;">
                                        ${callData.metrics.total_latency_ms ? callData.metrics.total_latency_ms.toFixed(2) + 'ms' : 
                                          (callData.metrics.tts_ttfb_ms && callData.metrics.stt_ttfb_ms && callData.metrics.llm_ttfb_ms) ? 
                                          (callData.metrics.tts_ttfb_ms + callData.metrics.stt_ttfb_ms + callData.metrics.llm_ttfb_ms).toFixed(2) + 'ms' : 'N/A'}
                                    </div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">Prompt Tokens</div>
                                    <div class="call-detail-value">${callData.metrics.total_prompt_tokens || 'N/A'}</div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">Completion Tokens</div>
                                    <div class="call-detail-value">${callData.metrics.total_completion_tokens || 'N/A'}</div>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${callData.cost ? `
                        <div style="margin-top: 20px;">
                            <h4 style="color: #ffffff; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Cost Breakdown</h4>
                            <div class="call-details" style="grid-template-columns: 1fr 1fr 1fr;">
                                <div class="call-detail">
                                    <div class="call-detail-label">LLM Cost</div>
                                    <div class="call-detail-value">${callData.cost.llm_cost ? '$' + callData.cost.llm_cost.toFixed(4) : 'N/A'}</div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">TTS Cost</div>
                                    <div class="call-detail-value">${callData.cost.tts_cost ? '$' + callData.cost.tts_cost.toFixed(4) : 'N/A'}</div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">STT Cost</div>
                                    <div class="call-detail-value">${callData.cost.stt_cost ? '$' + callData.cost.stt_cost.toFixed(4) : 'N/A'}</div>
                                </div>
                                <div class="call-detail">
                                    <div class="call-detail-label">Total Cost</div>
                                    <div class="call-detail-value" style="color: #fbbf24; font-weight: 700;">
                                        ${callData.cost.total_cost ? '$' + callData.cost.total_cost.toFixed(4) : 
                                          (callData.cost.llm_cost && callData.cost.tts_cost && callData.cost.stt_cost) ? 
                                          '$' + (callData.cost.llm_cost + callData.cost.tts_cost + callData.cost.stt_cost).toFixed(4) : 'N/A'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${callData.transcript ? `
                        <div class="call-transcript">
                            <div class="transcript-header">
                                <strong>Transcript:</strong>
                                <button class="copy-transcript-btn" onclick="copyTranscript()">Copy</button>
                            </div>
                            <textarea readonly id="transcriptTextarea">${callData.transcript}</textarea>
                        </div>
                    ` : ''}
                    
                    ${callData.recording_url ? `
                        <div class="call-audio">
                            <audio controls class="audio-player">
                                <source src="${callData.recording_url}" type="audio/wav">
                                Your browser does not support the audio element.
                            </audio>
                            <a href="${callData.recording_url}" download class="download-btn">Download</a>
                        </div>
                    ` : ''}
                </div>
            `;
            
            dialog.style.display = 'flex';
        }
        
        function closeCallDetailsDialog() {
            const dialog = document.getElementById('callDetailsDialog');
            dialog.style.display = 'none';
        }
        
        // Dialog event listeners
        document.getElementById('closeDialogBtn').addEventListener('click', closeCallDetailsDialog);
        document.getElementById('callDetailsDialog').addEventListener('click', (e) => {
            if (e.target.id === 'callDetailsDialog') {
                closeCallDetailsDialog();
            }
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
        
        // Copy transcript function
        async function copyTranscript() {
            const textarea = document.getElementById('transcriptTextarea');
            if (textarea) {
                try {
                    // Try modern clipboard API first
                    if (navigator.clipboard && window.isSecureContext) {
                        await navigator.clipboard.writeText(textarea.value);
                        showMessage('Transcript copied to clipboard!', 'success');
                    } else {
                        // Fallback for older browsers
                        textarea.select();
                        textarea.setSelectionRange(0, 99999);
                        document.execCommand('copy');
                        showMessage('Transcript copied to clipboard!', 'success');
                    }
                } catch (err) {
                    console.error('Failed to copy transcript:', err);
                    showMessage('Failed to copy transcript', 'error');
                }
            }
        }
        
        // Make copy function available globally
        window.copyTranscript = copyTranscript;
        
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
            loadCurrentPrompt('standard');
            loadCurrentPrompt('multimodel');
            
            // Initialize provider dropdown visibility based on current bot type
            const botType = document.getElementById('botType').value;
            const providerDropdowns = document.getElementById('providerDropdowns');
            if (botType === 'standard') {
                providerDropdowns.classList.add('show');
            } else {
                providerDropdowns.classList.remove('show');
            }
            
            // Load latest calls on page load
            loadLatestCalls();
        });
    </script>
</body>
</html>
"""
