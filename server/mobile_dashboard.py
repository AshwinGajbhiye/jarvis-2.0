"""
J.A.R.V.I.S. Mobile Dashboard & PWA App
Stark Industries HUD-inspired responsive mobile web & standalone installable application.
"""

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>J.A.R.V.I.S.</title>

    <!-- PWA & Mobile Standalone Tags -->
    <link rel="manifest" href="/manifest.json">
    <link rel="icon" type="image/png" href="/icon-192.png">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="J.A.R.V.I.S.">
    <meta name="theme-color" content="#00f0ff">
    <meta name="mobile-web-app-capable" content="yes">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #050b14;
            --bg-card: rgba(10, 25, 47, 0.7);
            --bg-card-border: rgba(0, 240, 255, 0.25);
            --cyan-glow: #00f0ff;
            --cyan-dim: rgba(0, 240, 255, 0.15);
            --amber-glow: #ffb703;
            --emerald-glow: #06d6a0;
            --red-alert: #ef476f;
            --text-main: #e2f1f8;
            --text-dim: #7da5bf;
            --font-display: 'Orbitron', -apple-system, sans-serif;
            --font-sub: 'Rajdhani', -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg-primary);
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(0, 240, 255, 0.12) 0%, transparent 60%),
                linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
            background-size: 100% 100%, 24px 24px, 24px 24px;
            color: var(--text-main);
            font-family: var(--font-sub);
            font-size: 16px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            padding-bottom: env(safe-area-inset-bottom, 20px);
            padding-top: env(safe-area-inset-top, 0px);
        }

        /* Top Bar */
        header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(5, 11, 20, 0.85);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--bg-card-border);
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .mini-reactor {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 2px solid var(--cyan-glow);
            box-shadow: 0 0 10px var(--cyan-glow);
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulse-ring 3s infinite alternate;
        }

        .mini-reactor-core {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #fff;
            box-shadow: 0 0 8px #fff;
        }

        .logo-title {
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 18px;
            letter-spacing: 2px;
            color: var(--cyan-glow);
            text-shadow: 0 0 8px rgba(0, 240, 255, 0.5);
        }

        .system-indicators {
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: var(--font-mono);
            font-size: 12px;
        }

        .install-pwa-btn {
            background: linear-gradient(135deg, var(--cyan-glow), #0077b6);
            border: 1px solid var(--cyan-glow);
            color: #050b14;
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 0.5px;
            border-radius: 6px;
            padding: 5px 10px;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.4);
            animation: pulse-ring 2s infinite alternate;
        }

        .install-pwa-btn.installed {
            background: rgba(255, 183, 3, 0.15);
            border-color: var(--amber-glow);
            color: var(--amber-glow);
            box-shadow: none;
            animation: none;
            cursor: default;
        }

        .status-badge {
            padding: 4px 8px;
            border-radius: 6px;
            background: rgba(6, 214, 160, 0.15);
            border: 1px solid var(--emerald-glow);
            color: var(--emerald-glow);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--emerald-glow);
            box-shadow: 0 0 6px var(--emerald-glow);
        }

        .key-btn {
            background: rgba(0, 240, 255, 0.1);
            border: 1px solid var(--cyan-glow);
            color: var(--cyan-glow);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
        }

        /* Navigation Tabs */
        .nav-tabs {
            display: flex;
            background: rgba(5, 15, 30, 0.9);
            border-bottom: 1px solid var(--bg-card-border);
            padding: 4px 8px;
            gap: 6px;
            overflow-x: auto;
        }

        .nav-tab {
            flex: 1;
            min-width: 80px;
            text-align: center;
            padding: 10px 4px;
            font-family: var(--font-display);
            font-size: 11px;
            letter-spacing: 1px;
            color: var(--text-dim);
            background: transparent;
            border: 1px solid transparent;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }

        .nav-tab.active {
            color: var(--cyan-glow);
            background: rgba(0, 240, 255, 0.12);
            border-color: rgba(0, 240, 255, 0.4);
            box-shadow: 0 0 12px rgba(0, 240, 255, 0.2);
        }

        /* Main Containers */
        main {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            max-width: 700px;
            margin: 0 auto;
            width: 100%;
        }

        .tab-panel {
            display: none;
            flex-direction: column;
            gap: 16px;
        }

        .tab-panel.active {
            display: flex;
        }

        /* Glass Cards */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--bg-card-border);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
            position: relative;
            overflow: hidden;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            border-bottom: 1px solid rgba(0, 240, 255, 0.15);
            padding-bottom: 8px;
        }

        .card-title {
            font-family: var(--font-display);
            font-size: 13px;
            letter-spacing: 1.5px;
            color: var(--cyan-glow);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Arc Reactor Center */
        .reactor-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px 0;
        }

        .arc-reactor-btn {
            width: 110px;
            height: 110px;
            border-radius: 50%;
            background: radial-gradient(circle, #09203f 0%, #050b14 100%);
            border: 3px solid var(--cyan-glow);
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.4), inset 0 0 15px rgba(0, 240, 255, 0.4);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            outline: none;
        }

        .arc-reactor-btn.recording {
            border-color: var(--red-alert);
            box-shadow: 0 0 30px rgba(239, 71, 111, 0.8), inset 0 0 20px rgba(239, 71, 111, 0.6);
            animation: pulse-recording 1s infinite alternate;
        }

        .arc-reactor-btn svg {
            width: 38px;
            height: 38px;
            fill: var(--cyan-glow);
            transition: all 0.3s;
        }

        .arc-reactor-btn.recording svg {
            fill: var(--red-alert);
        }

        .reactor-label {
            margin-top: 12px;
            font-family: var(--font-display);
            font-size: 12px;
            letter-spacing: 1.5px;
            color: var(--text-dim);
        }

        /* Quick Chips */
        .chips-scroll {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 4px;
        }

        .chip {
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.25);
            color: var(--text-main);
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 13px;
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.2s;
        }

        .chip:hover, .chip:active {
            background: rgba(0, 240, 255, 0.25);
            border-color: var(--cyan-glow);
            color: #fff;
        }

        /* Chat Feed */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 320px;
            overflow-y: auto;
            gap: 12px;
            padding-right: 4px;
        }

        .chat-bubble {
            max-width: 85%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.4;
            word-break: break-word;
        }

        .chat-bubble.user {
            align-self: flex-end;
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.25), rgba(0, 119, 182, 0.35));
            border: 1px solid var(--cyan-glow);
            color: #fff;
            border-bottom-right-radius: 2px;
        }

        .chat-bubble.jarvis {
            align-self: flex-start;
            background: rgba(10, 25, 47, 0.85);
            border: 1px solid rgba(0, 240, 255, 0.2);
            color: var(--text-main);
            border-bottom-left-radius: 2px;
        }

        .chat-file-card {
            margin-top: 8px;
            background: rgba(0, 0, 0, 0.4);
            border: 1px dashed var(--cyan-glow);
            border-radius: 8px;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }

        .chat-file-name {
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--cyan-glow);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .download-action-btn {
            background: var(--cyan-glow);
            color: #050b14;
            font-family: var(--font-display);
            font-size: 11px;
            font-weight: 700;
            padding: 6px 12px;
            border-radius: 6px;
            text-decoration: none;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            border: none;
        }

        /* Input Controls */
        .chat-input-bar {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }

        .text-input {
            flex: 1;
            background: rgba(5, 15, 30, 0.8);
            border: 1px solid var(--bg-card-border);
            color: #fff;
            padding: 12px 14px;
            border-radius: 8px;
            font-family: var(--font-sub);
            font-size: 15px;
            outline: none;
        }

        .text-input:focus {
            border-color: var(--cyan-glow);
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
        }

        .send-btn {
            background: linear-gradient(135deg, var(--cyan-glow), #0077b6);
            border: none;
            color: #050b14;
            font-family: var(--font-display);
            font-weight: 700;
            padding: 0 18px;
            border-radius: 8px;
            cursor: pointer;
        }

        /* File Transfer Tab */
        .dropzone {
            border: 2px dashed rgba(0, 240, 255, 0.4);
            border-radius: 12px;
            padding: 24px 16px;
            text-align: center;
            background: rgba(0, 240, 255, 0.03);
            cursor: pointer;
            transition: all 0.2s;
        }

        .dropzone.dragover {
            background: rgba(0, 240, 255, 0.12);
            border-color: var(--cyan-glow);
            box-shadow: 0 0 16px rgba(0, 240, 255, 0.3);
        }

        .dropzone-icon {
            font-size: 36px;
            color: var(--cyan-glow);
            margin-bottom: 8px;
        }

        .dropzone-title {
            font-family: var(--font-display);
            font-size: 14px;
            color: var(--cyan-glow);
            margin-bottom: 4px;
        }

        .dropzone-desc {
            font-size: 13px;
            color: var(--text-dim);
        }

        .destination-select {
            margin-top: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
        }

        .custom-select {
            background: #09203f;
            color: #fff;
            border: 1px solid var(--bg-card-border);
            padding: 6px 12px;
            border-radius: 6px;
            outline: none;
            font-family: var(--font-sub);
        }

        .progress-bar-container {
            display: none;
            margin-top: 12px;
            height: 6px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-bar {
            width: 0%;
            height: 100%;
            background: var(--cyan-glow);
            transition: width 0.3s;
        }

        /* File Browser */
        .file-browser-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-height: 400px;
            overflow-y: auto;
        }

        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            background: rgba(5, 15, 30, 0.6);
            border: 1px solid rgba(0, 240, 255, 0.1);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .file-item:hover, .file-item:active {
            background: rgba(0, 240, 255, 0.1);
            border-color: rgba(0, 240, 255, 0.3);
        }

        .file-info {
            display: flex;
            align-items: center;
            gap: 10px;
            overflow: hidden;
        }

        .file-icon {
            font-size: 18px;
            flex-shrink: 0;
        }

        .file-title {
            font-family: var(--font-mono);
            font-size: 13px;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-meta {
            font-size: 11px;
            color: var(--text-dim);
        }

        /* Tasks Tab */
        .task-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .task-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(5, 15, 30, 0.6);
            border: 1px solid rgba(0, 240, 255, 0.15);
            padding: 10px 14px;
            border-radius: 8px;
        }

        .task-text {
            font-size: 15px;
        }

        .task-complete-btn {
            background: transparent;
            border: 1px solid var(--emerald-glow);
            color: var(--emerald-glow);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
        }

        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(8px);
            z-index: 200;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .modal-overlay.active {
            display: flex;
        }

        .modal-content {
            background: #0a192f;
            border: 1px solid var(--cyan-glow);
            box-shadow: 0 0 25px rgba(0, 240, 255, 0.3);
            border-radius: 12px;
            padding: 20px;
            max-width: 420px;
            width: 100%;
        }

        /* Toast notification */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: #050b14;
            border: 1px solid var(--cyan-glow);
            color: #fff;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 13px;
            z-index: 300;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.4);
            display: none;
        }

        @keyframes pulse-ring {
            0% { box-shadow: 0 0 6px var(--cyan-glow); }
            100% { box-shadow: 0 0 16px var(--cyan-glow); }
        }

        @keyframes pulse-recording {
            0% { transform: scale(1); }
            100% { transform: scale(1.06); }
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header>
        <div class="logo-group">
            <div class="mini-reactor">
                <div class="mini-reactor-core"></div>
            </div>
            <span class="logo-title">J.A.R.V.I.S.</span>
        </div>
        <div class="system-indicators">
            <button class="install-pwa-btn" id="install-app-btn" onclick="triggerInstallApp()">📲 INSTALL</button>
            <div class="status-badge" id="system-status-badge">
                <div class="status-dot"></div>
                <span id="status-text">ONLINE</span>
            </div>
            <button class="key-btn" onclick="openKeyModal()">🔑 KEY</button>
        </div>
    </header>

    <!-- Tabs Navigation -->
    <div class="nav-tabs">
        <button class="nav-tab active" onclick="switchTab('tab-terminal')">TERMINAL</button>
        <button class="nav-tab" onclick="switchTab('tab-files')">FILE TRANSFER</button>
        <button class="nav-tab" onclick="switchTab('tab-tasks')">TASKS</button>
        <button class="nav-tab" onclick="switchTab('tab-system')">SYSTEM</button>
    </div>

    <!-- Main Views -->
    <main>
        <!-- Tab 1: Terminal & Voice -->
        <section id="tab-terminal" class="tab-panel active">
            <!-- Arc Reactor Voice Center -->
            <div class="card reactor-section">
                <button class="arc-reactor-btn" id="voice-btn" onclick="toggleVoiceRecording()">
                    <svg viewBox="0 0 24 24">
                        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                    </svg>
                </button>
                <div class="reactor-label" id="voice-label">TAP TO SPEAK TO JARVIS</div>
            </div>

            <!-- Quick Suggestions -->
            <div class="chips-scroll">
                <div class="chip" onclick="sendQuickCommand('Send me notes.txt')">📄 Get notes.txt</div>
                <div class="chip" onclick="sendQuickCommand('What time is it?')">⏰ Time</div>
                <div class="chip" onclick="sendQuickCommand('What is my battery level?')">🔋 Battery</div>
                <div class="chip" onclick="sendQuickCommand('Read my emails')">📧 Emails</div>
            </div>

            <!-- Chat Console -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">💬 QUANTUM COMMUNICATIONS FEED</span>
                    <span style="font-size:12px; color:var(--text-dim);" id="connection-ip">Local</span>
                </div>
                <div class="chat-container" id="chat-container">
                    <div class="chat-bubble jarvis">
                        At your service, Sir. Voice interface and mobile file transfer channels are fully synchronized.
                    </div>
                </div>
                <div class="chat-input-bar">
                    <input type="text" class="text-input" id="chat-input" placeholder="Transmit command..." onkeypress="handleEnter(event)">
                    <button class="send-btn" onclick="sendTextCommand()">SEND</button>
                </div>
            </div>
        </section>

        <!-- Tab 2: File Transfer Hub -->
        <section id="tab-files" class="tab-panel">
            <!-- Mobile -> Mac Upload Card -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📤 UPLOAD TO MAC</span>
                    <span style="font-size: 12px; color: var(--emerald-glow);">MOBILE ➔ MAC</span>
                </div>

                <div class="dropzone" id="dropzone" onclick="document.getElementById('file-upload-input').click()">
                    <div class="dropzone-icon">📥</div>
                    <div class="dropzone-title">TAP OR DROP FILE TO SEND TO MAC</div>
                    <div class="dropzone-desc">Photos, documents, or media will be delivered straight to your Mac</div>
                    <input type="file" id="file-upload-input" style="display:none;" onchange="handleFileUpload(this.files)">
                </div>

                <div class="destination-select">
                    <span>Save to Mac:</span>
                    <select id="upload-destination" class="custom-select">
                        <option value="Downloads">~/Downloads</option>
                        <option value="Desktop">~/Desktop</option>
                        <option value="Documents">~/Documents</option>
                    </select>
                </div>

                <div class="progress-bar-container" id="upload-progress-container">
                    <div class="progress-bar" id="upload-progress-bar"></div>
                </div>
            </div>

            <!-- Recent Received Downloads -->
            <div class="card" id="recent-download-card" style="display:none;">
                <div class="card-header">
                    <span class="card-title">📥 DISPATCHED FROM MAC</span>
                </div>
                <div id="recent-download-content"></div>
            </div>

            <!-- Mac Remote File Explorer -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🗂️ MAC REMOTE EXPLORER</span>
                    <button class="key-btn" onclick="fetchFiles('')">HOME</button>
                </div>
                <div style="font-family:var(--font-mono); font-size:12px; margin-bottom:8px; color:var(--cyan-glow);" id="current-explorer-path">~/</div>
                <div class="file-browser-list" id="file-browser-list">
                    <div style="color:var(--text-dim); text-align:center; padding:20px;">Scanning Mac filesystem...</div>
                </div>
            </div>
        </section>

        <!-- Tab 3: Tasks & Reminders -->
        <section id="tab-tasks" class="tab-panel">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📋 ACTIVE MISSIONS & TASKS</span>
                </div>
                <div class="chat-input-bar" style="margin-bottom:12px;">
                    <input type="text" class="text-input" id="new-task-input" placeholder="New mission objective...">
                    <button class="send-btn" onclick="addNewTask()">ADD</button>
                </div>
                <div class="task-list" id="task-list-container">
                    <div style="color:var(--text-dim); text-align:center; padding:10px;">Loading tasks...</div>
                </div>
            </div>
        </section>

        <!-- Tab 4: System & Quick Controls -->
        <section id="tab-system" class="tab-panel">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">⚡ MAC TELEMETRY</span>
                </div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-family:var(--font-mono);">
                    <div style="background:rgba(0,0,0,0.4); padding:12px; border-radius:8px;">
                        <div style="color:var(--text-dim); font-size:11px;">BATTERY</div>
                        <div id="sys-battery" style="color:var(--cyan-glow); font-size:18px; margin-top:4px;">--</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.4); padding:12px; border-radius:8px;">
                        <div style="color:var(--text-dim); font-size:11px;">CPU LOAD</div>
                        <div id="sys-load" style="color:var(--amber-glow); font-size:18px; margin-top:4px;">--</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.4); padding:12px; border-radius:8px;">
                        <div style="color:var(--text-dim); font-size:11px;">MODEL</div>
                        <div id="sys-model" style="color:var(--emerald-glow); font-size:14px; margin-top:4px;">--</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.4); padding:12px; border-radius:8px;">
                        <div style="color:var(--text-dim); font-size:11px;">AI BACKEND</div>
                        <div id="sys-backend" style="color:#fff; font-size:14px; margin-top:4px;">--</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">🎛️ QUICK MAC ACTIONS</span>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:8px;">
                    <button class="key-btn" style="padding:10px 14px;" onclick="sendQuickCommand('Set volume to 50%')">🔊 Vol 50%</button>
                    <button class="key-btn" style="padding:10px 14px;" onclick="sendQuickCommand('Mute the Mac')">🔇 Mute</button>
                    <button class="key-btn" style="padding:10px 14px;" onclick="sendQuickCommand('Open Google Chrome')">🌐 Chrome</button>
                    <button class="key-btn" style="padding:10px 14px;" onclick="sendQuickCommand('Open VS Code')">💻 VS Code</button>
                </div>
            </div>
        </section>
    </main>

    <!-- PWA Install Modal -->
    <div class="modal-overlay" id="install-modal">
        <div class="modal-content">
            <h3 style="font-family:var(--font-display); color:var(--cyan-glow); margin-bottom:12px; display:flex; align-items:center; gap:8px;">
                <span>📲</span> INSTALL J.A.R.V.I.S. APP
            </h3>
            <div id="install-instructions" style="font-size:14px; line-height:1.6; color:var(--text-main); margin-bottom:16px;">
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button class="send-btn" onclick="closeInstallModal()">GOT IT</button>
            </div>
        </div>
    </div>

    <!-- Key Config Modal -->
    <div class="modal-overlay" id="key-modal">
        <div class="modal-content">
            <h3 style="font-family:var(--font-display); color:var(--cyan-glow); margin-bottom:12px;">SECURITY CREDENTIALS</h3>
            <p style="font-size:13px; color:var(--text-dim); margin-bottom:12px;">Enter your Jarvis Mobile API Key configured on your Mac.</p>
            <input type="text" id="api-key-input" class="text-input" style="width:100%; margin-bottom:16px;" placeholder="API Key">
            <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button class="key-btn" onclick="closeKeyModal()">CANCEL</button>
                <button class="send-btn" onclick="saveApiKey()">SAVE KEY</button>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toast-notify"></div>

    <script>
        // State
        let apiKey = localStorage.getItem('jarvis_mobile_key') || 'jarvis-mobile-secret-key-2026';
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        let deferredPrompt = null;
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

        // Register Service Worker for PWA
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(e => console.log('SW registration note:', e));
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            const btn = document.getElementById('install-app-btn');
            if (btn) btn.style.display = 'inline-block';
        });

        // Check URL for ?key=... parameter
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('key')) {
            apiKey = urlParams.get('key');
            localStorage.setItem('jarvis_mobile_key', apiKey);
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            pingJarvis();
            fetchFiles('');
            fetchTasks();
            fetchSystemTelemetry();
            checkStandaloneMode();
        });

        function checkStandaloneMode() {
            const btn = document.getElementById('install-app-btn');
            if (isStandalone && btn) {
                btn.innerText = '⚡ APP MODE';
                btn.classList.add('installed');
            }
        }

        function triggerInstallApp() {
            if (isStandalone) {
                showToast('J.A.R.V.I.S. is already running in native App Mode!');
                return;
            }

            if (deferredPrompt) {
                // Native Android / Chrome prompt
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        showToast('J.A.R.V.I.S. App Installed!');
                    }
                    deferredPrompt = null;
                });
            } else {
                const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
                const container = document.getElementById('install-instructions');
                if (isIOS) {
                    container.innerHTML = `
                        <p style="margin-bottom:12px; font-weight:600;">To install Jarvis as a native app on your iPhone:</p>
                        <ol style="padding-left:20px; display:flex; flex-direction:column; gap:8px;">
                            <li>Tap the <strong>Share</strong> button <span style="font-size:18px;">⎋</span> at the bottom of Safari.</li>
                            <li>Scroll down and tap <strong>"Add to Home Screen"</strong> <span style="font-size:18px;">➕</span>.</li>
                            <li>Tap <strong>"Add"</strong> in the top right corner.</li>
                        </ol>
                        <p style="margin-top:14px; color:var(--cyan-glow); font-size:13px;">
                            ⭐ Jarvis will appear on your iPhone Home Screen with its own Arc Reactor icon and open full-screen without any browser address bar!
                        </p>
                    `;
                } else {
                    container.innerHTML = `
                        <p style="margin-bottom:12px; font-weight:600;">To install Jarvis on your phone:</p>
                        <ol style="padding-left:20px; display:flex; flex-direction:column; gap:8px;">
                            <li>Open your mobile browser menu (<strong>⋮</strong> three dots in Chrome).</li>
                            <li>Tap <strong>"Install app"</strong> or <strong>"Add to Home screen"</strong>.</li>
                            <li>Confirm installation.</li>
                        </ol>
                        <p style="margin-top:14px; color:var(--cyan-glow); font-size:13px;">
                            ⭐ Jarvis will be installed as a standalone mobile application on your device!
                        </p>
                    `;
                }
                document.getElementById('install-modal').classList.add('active');
            }
        }

        function closeInstallModal() {
            document.getElementById('install-modal').classList.remove('active');
        }

        function showToast(msg) {
            const toast = document.getElementById('toast-notify');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 3000);
        }

        function switchTab(tabId) {
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');

            if (tabId === 'tab-files') fetchFiles('');
            if (tabId === 'tab-tasks') fetchTasks();
            if (tabId === 'tab-system') fetchSystemTelemetry();
        }

        function openKeyModal() {
            document.getElementById('api-key-input').value = apiKey;
            document.getElementById('key-modal').classList.add('active');
        }

        function closeKeyModal() {
            document.getElementById('key-modal').classList.remove('active');
        }

        function saveApiKey() {
            apiKey = document.getElementById('api-key-input').value.trim();
            localStorage.setItem('jarvis_mobile_key', apiKey);
            closeKeyModal();
            showToast('API Key Updated');
            pingJarvis();
        }

        async function pingJarvis() {
            try {
                const res = await fetch('/api/ping', {
                    headers: { 'x-api-key': apiKey }
                });
                if (res.ok) {
                    document.getElementById('system-status-badge').style.borderColor = 'var(--emerald-glow)';
                    document.getElementById('status-text').innerText = 'ONLINE';
                } else {
                    document.getElementById('system-status-badge').style.borderColor = 'var(--red-alert)';
                    document.getElementById('status-text').innerText = 'AUTH REQUIRED';
                }
            } catch (e) {
                document.getElementById('system-status-badge').style.borderColor = 'var(--red-alert)';
                document.getElementById('status-text').innerText = 'OFFLINE';
            }
        }

        // Chat & Commands
        function appendChatMessage(sender, text, isUser = false, fileUrl = null, fileName = null) {
            const container = document.getElementById('chat-container');
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble ' + (isUser ? 'user' : 'jarvis');
            
            let html = text.replace(/\\n/g, '<br>');
            if (fileUrl) {
                const downloadLink = fileUrl + '&api_key=' + encodeURIComponent(apiKey);
                html += `
                    <div class="chat-file-card">
                        <span class="chat-file-name">📦 ${fileName || 'Mac File'}</span>
                        <a href="${downloadLink}" class="download-action-btn" download>DOWNLOAD</a>
                    </div>
                `;
                displayRecentDownload(fileName, downloadLink);
            }
            bubble.innerHTML = html;
            container.appendChild(bubble);
            container.scrollTop = container.scrollHeight;
        }

        function handleEnter(e) {
            if (e.key === 'Enter') sendTextCommand();
        }

        async function sendTextCommand() {
            const input = document.getElementById('chat-input');
            const command = input.value.trim();
            if (!command) return;
            
            input.value = '';
            appendChatMessage('You', command, true);

            try {
                const res = await fetch('/api/command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-api-key': apiKey
                    },
                    body: JSON.stringify({ command: command })
                });
                
                const data = await res.json();
                if (res.ok) {
                    appendChatMessage('Jarvis', data.response, false, data.file_url, data.file_name);
                } else {
                    appendChatMessage('Jarvis', `⚠️ Error: ${data.detail || 'Command failed'}`, false);
                }
            } catch (err) {
                appendChatMessage('Jarvis', `⚠️ Connection error: ${err.message}`, false);
            }
        }

        function sendQuickCommand(cmd) {
            document.getElementById('chat-input').value = cmd;
            sendTextCommand();
        }

        // Voice Recording via MediaRecorder
        async function toggleVoiceRecording() {
            const btn = document.getElementById('voice-btn');
            const label = document.getElementById('voice-label');

            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = (e) => {
                        if (e.data.size > 0) audioChunks.push(e.data);
                    };

                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        uploadVoiceNote(audioBlob);
                        stream.getTracks().forEach(track => track.stop());
                    };

                    mediaRecorder.start();
                    isRecording = true;
                    btn.classList.add('recording');
                    label.innerText = 'RECORDING... TAP TO TRANSMIT';
                } catch (e) {
                    showToast('Microphone access denied');
                }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                btn.classList.remove('recording');
                label.innerText = 'PROCESSING VOICE...';
            }
        }

        async function uploadVoiceNote(blob) {
            const label = document.getElementById('voice-label');
            const formData = new FormData();
            formData.append('audio', blob, 'mobile_voice.webm');

            try {
                const res = await fetch('/api/voice-command', {
                    method: 'POST',
                    headers: { 'x-api-key': apiKey },
                    body: formData
                });
                const data = await res.json();
                label.innerText = 'TAP TO SPEAK TO JARVIS';

                if (res.ok) {
                    if (data.text_recognized) {
                        appendChatMessage('You (Voice)', data.text_recognized, true);
                    }
                    appendChatMessage('Jarvis', data.response, false, data.file_url, data.file_name);
                } else {
                    appendChatMessage('Jarvis', `⚠️ Voice error: ${data.detail}`, false);
                }
            } catch (err) {
                label.innerText = 'TAP TO SPEAK TO JARVIS';
                showToast('Voice transmission error');
            }
        }

        // File Transfer: Mobile -> Mac Upload
        async function handleFileUpload(files) {
            if (!files || !files.length) return;
            const file = files[0];
            const destination = document.getElementById('upload-destination').value;

            const progressBar = document.getElementById('upload-progress-bar');
            const progressContainer = document.getElementById('upload-progress-container');
            progressContainer.style.display = 'block';
            progressBar.style.width = '30%';

            const formData = new FormData();
            formData.append('file', file);

            try {
                progressBar.style.width = '60%';
                const res = await fetch(`/api/upload?destination=${encodeURIComponent(destination)}`, {
                    method: 'POST',
                    headers: { 'x-api-key': apiKey },
                    body: formData
                });
                progressBar.style.width = '100%';
                const data = await res.json();
                setTimeout(() => { progressContainer.style.display = 'none'; progressBar.style.width = '0%'; }, 1000);

                if (res.ok) {
                    showToast(`Uploaded ${data.filename} to ~/${destination}`);
                    appendChatMessage('System', `📥 Uploaded '${data.filename}' to Mac ~/${destination}`);
                    fetchFiles(destination);
                } else {
                    showToast(`Upload failed: ${data.detail}`);
                }
            } catch (e) {
                progressContainer.style.display = 'none';
                showToast('Upload error: ' + e.message);
            }
        }

        function displayRecentDownload(filename, url) {
            const card = document.getElementById('recent-download-card');
            const content = document.getElementById('recent-download-content');
            card.style.display = 'block';
            content.innerHTML = `
                <div class="chat-file-card">
                    <span class="chat-file-name">📦 ${filename}</span>
                    <a href="${url}" class="download-action-btn" download>DOWNLOAD TO PHONE</a>
                </div>
            `;
        }

        // Mac Remote File Explorer
        async function fetchFiles(subpath) {
            const listEl = document.getElementById('file-browser-list');
            const pathLabel = document.getElementById('current-explorer-path');
            pathLabel.innerText = '~/' + (subpath || '');

            try {
                const res = await fetch(`/api/files?path=${encodeURIComponent(subpath)}`, {
                    headers: { 'x-api-key': apiKey }
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);

                listEl.innerHTML = '';
                if (data.parent_path !== null && subpath !== "") {
                    const upItem = document.createElement('div');
                    upItem.className = 'file-item';
                    upItem.innerHTML = `
                        <div class="file-info">
                            <span class="file-icon">📁</span>
                            <span class="file-title">.. (Parent Directory)</span>
                        </div>
                    `;
                    upItem.onclick = () => fetchFiles(data.parent_path);
                    listEl.appendChild(upItem);
                }

                if (!data.items || data.items.length === 0) {
                    listEl.innerHTML = '<div style="color:var(--text-dim); text-align:center; padding:15px;">Empty folder</div>';
                    return;
                }

                data.items.forEach(item => {
                    const el = document.createElement('div');
                    el.className = 'file-item';
                    const icon = item.is_dir ? '📁' : '📄';
                    const downloadBtn = item.is_dir ? '' : `
                        <a href="${item.download_url}&api_key=${encodeURIComponent(apiKey)}" class="download-action-btn" download onclick="event.stopPropagation()">GET</a>
                    `;

                    el.innerHTML = `
                        <div class="file-info">
                            <span class="file-icon">${icon}</span>
                            <div>
                                <div class="file-title">${item.name}</div>
                                <div class="file-meta">${item.size || (item.is_dir ? 'Folder' : '')}</div>
                            </div>
                        </div>
                        ${downloadBtn}
                    `;
                    if (item.is_dir) {
                        el.onclick = () => fetchFiles(item.path);
                    }
                    listEl.appendChild(el);
                });
            } catch (err) {
                listEl.innerHTML = `<div style="color:var(--red-alert); text-align:center; padding:15px;">Unable to load files: ${err.message}</div>`;
            }
        }

        // Tasks
        async function fetchTasks() {
            const container = document.getElementById('task-list-container');
            try {
                const res = await fetch('/api/tasks', {
                    headers: { 'x-api-key': apiKey }
                });
                const data = await res.json();
                const tasks = data.tasks || [];
                container.innerHTML = '';
                if (tasks.length === 0) {
                    container.innerHTML = '<div style="color:var(--text-dim); text-align:center; padding:10px;">No pending missions.</div>';
                    return;
                }
                tasks.forEach(t => {
                    const el = document.createElement('div');
                    el.className = 'task-item';
                    el.innerHTML = `
                        <span class="task-text">${t.task || t}</span>
                        <button class="task-complete-btn" onclick="completeTask(${t.id || 0})">DONE</button>
                    `;
                    container.appendChild(el);
                });
            } catch (e) {
                container.innerHTML = '<div style="color:var(--text-dim); text-align:center;">Failed to load tasks</div>';
            }
        }

        async function addNewTask() {
            const input = document.getElementById('new-task-input');
            const task = input.value.trim();
            if (!task) return;
            input.value = '';
            await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
                body: JSON.stringify({ task: task })
            });
            fetchTasks();
            showToast('Task added');
        }

        async function completeTask(taskId) {
            await fetch('/api/tasks/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
                body: JSON.stringify({ task_id: taskId })
            });
            fetchTasks();
            showToast('Task completed');
        }

        // System Telemetry
        async function fetchSystemTelemetry() {
            try {
                const res = await fetch('/api/status', {
                    headers: { 'x-api-key': apiKey }
                });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('sys-battery').innerText = data.battery || '100%';
                    document.getElementById('sys-load').innerText = data.load || 'Nominal';
                    document.getElementById('sys-model').innerText = data.model || 'Gemini 3.5';
                    document.getElementById('sys-backend').innerText = data.antigravity ? 'Antigravity SDK' : 'Gemini Engine';
                }
            } catch (e) {}
        }
    </script>
</body>
</html>
"""
