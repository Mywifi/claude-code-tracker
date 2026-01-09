import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Tracker - AI Interactions</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown-dark.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        
        :root {
            --claude-bg: #1A1A1A;
            --claude-sidebar: #111111;
            --claude-accent: #D97706; /* Amber-600 */
            --claude-text: #E5E5E5;
            --claude-text-muted: #A3A3A3;
            --claude-border: #333333;
            --claude-card: #262626;
            --claude-user-bg: #1e293b;
            --claude-ai-bg: #262626;
            --claude-system-bg: #2e2417;
            --claude-system-border: #78350f;
        }

        body { 
            background-color: var(--claude-bg); 
            color: var(--claude-text);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }

        .markdown-body { 
            background-color: transparent !important; 
            font-size: 14px; 
            color: var(--claude-text) !important;
        }
        
        .markdown-body pre { 
            background-color: #0c0c0c !important; 
            border: 1px solid var(--claude-border) !important;
        }
        
        .markdown-body code { 
            font-family: 'JetBrains Mono', monospace; 
            background-color: rgba(255, 255, 255, 0.1); 
        }

        .message-user { 
            background-color: var(--claude-user-bg); 
            border: 1px solid #334155;
            border-left: 4px solid #3b82f6;
        }
        
        .message-assistant { 
            background-color: var(--claude-ai-bg); 
            border: 1px solid var(--claude-border);
            border-left: 4px solid var(--claude-accent);
        }
        
        .message-system { 
            background-color: var(--claude-system-bg); 
            border: 1px solid var(--claude-system-border);
            border-left: 4px solid var(--claude-accent);
            color: #fde68a !important;
        }

        /* 侧边栏样式覆盖 */
        #prompt-list > div.bg-blue-50 {
            background-color: #262626 !important;
            border-left-color: var(--claude-accent) !important;
        }
        
        #prompt-list > div:hover {
            background-color: #262626;
        }

        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #444;
            border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body class="min-h-screen overflow-hidden">
    <div class="max-w-[1600px] mx-auto flex h-screen overflow-hidden border-x border-[#333]">
        <!-- 侧边栏 -->
        <div class="w-80 bg-[#111] border-r border-[#333] flex flex-col">
            <div class="p-6 border-b border-[#333] bg-[#111]">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-3 h-3 bg-amber-600 rounded-full animate-pulse"></div>
                    <h1 class="text-xl font-bold tracking-tight text-white">Claude Tracker</h1>
                </div>
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-neutral-500" id="summary-info">INITIALIZING...</p>
            </div>
            <div class="flex-1 overflow-y-auto custom-scrollbar" id="prompt-list">
                <!-- 列表项将在这里动态生成 -->
            </div>
        </div>

        <!-- 主内容区 -->
        <div class="flex-1 bg-[#1A1A1A] flex flex-col" id="detail-view">
            <div id="welcome-message" class="flex flex-col items-center justify-center h-full text-neutral-600">
                <svg class="w-20 h-20 mb-6 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path>
                </svg>
                <p class="text-lg font-medium tracking-wide">Select a session to analyze</p>
            </div>
            
            <div id="content-area" class="hidden flex-1 flex flex-col overflow-hidden">
                <div class="bg-[#1A1A1A] z-20 px-10 pt-10 pb-6 border-b border-[#333] shadow-lg">
                    <div class="max-w-5xl mx-auto">
                        <div class="flex justify-between items-start">
                            <div class="space-y-1">
                                <h2 class="text-3xl font-bold text-white tracking-tight" id="detail-model">MODEL</h2>
                                <div class="flex items-center gap-4">
                                    <p class="text-neutral-500 text-xs font-mono" id="detail-time">TIMESTAMP</p>
                                    <span class="text-[#333]">/</span>
                                    <p class="text-amber-600 text-xs font-black uppercase tracking-widest" id="detail-user-id">USER</p>
                                </div>
                            </div>
                            <div class="flex gap-2">
                                <span id="badge-stream" class="px-3 py-1 rounded-sm text-[10px] font-black bg-amber-600/10 text-amber-600 border border-amber-600/20 uppercase tracking-widest">Streaming</span>
                            </div>
                        </div>

                        <!-- Tab 切换 -->
                        <div class="flex gap-6 mt-8">
                            <button onclick="switchTab('render')" id="tab-render" class="pb-2 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2 border-amber-600 text-white">
                                Visual Render
                            </button>
                            <button onclick="switchTab('raw')" id="tab-raw" class="pb-2 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2 border-transparent text-neutral-500 hover:text-neutral-300">
                                Raw Analysis
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 可滚动的内容区域 -->
                <div class="flex-1 overflow-y-auto p-10 custom-scrollbar relative scroll-smooth" id="scroll-container">
                    <div class="max-w-5xl mx-auto pb-32 flex gap-12">
                        <div id="view-render" class="flex-1 space-y-12 min-w-0">
                            <!-- 系统提示词 -->
                            <div id="section-system">
                                <h3 class="text-xs font-black text-neutral-500 uppercase tracking-[0.3em] mb-6 flex items-center">
                                    <span class="w-8 h-[1px] bg-amber-600/30 mr-4"></span>
                                    System Directives
                                </h3>
                                <div id="system-container" class="space-y-4"></div>
                            </div>

                            <!-- 对话内容 -->
                            <div id="section-messages">
                                <h3 class="text-xs font-black text-neutral-500 uppercase tracking-[0.3em] mb-6 flex items-center">
                                    <span class="w-8 h-[1px] bg-blue-600/30 mr-4"></span>
                                    Interaction Log
                                </h3>
                                <div id="messages-container" class="space-y-10"></div>
                            </div>

                            <!-- AI 响应内容 -->
                            <div id="section-response">
                                <h3 class="text-xs font-black text-neutral-500 uppercase tracking-[0.3em] mb-6 flex items-center">
                                    <span class="w-8 h-[1px] bg-green-600/30 mr-4"></span>
                                    Final Response
                                </h3>
                                <div id="thinking-container" class="mb-6 hidden">
                                    <div class="bg-[#2e2417] border border-amber-900/50 rounded-lg overflow-hidden">
                                        <div class="bg-amber-900/20 px-4 py-2 flex items-center gap-2 border-b border-amber-900/30">
                                            <svg class="w-3 h-3 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                                            </svg>
                                            <span class="text-[9px] font-black text-amber-500 uppercase tracking-[0.2em]">Thinking Process</span>
                                        </div>
                                        <div id="thinking-content" class="p-5 text-sm text-amber-200/80 italic leading-relaxed"></div>
                                    </div>
                                </div>
                                <div id="response-container" class="space-y-4"></div>
                            </div>

                            <!-- 工具定义 -->
                            <div class="hidden" id="tools-section">
                                <h3 class="text-xs font-black text-neutral-500 uppercase tracking-[0.3em] mb-6 flex items-center">
                                    <span class="w-8 h-[1px] bg-purple-600/30 mr-4"></span>
                                    Tool Definitions
                                </h3>
                                <div id="tools-container" class="space-y-4"></div>
                            </div>
                        </div>

                        <!-- 目录 TOC -->
                        <div id="toc-container" class="w-48 shrink-0 hidden lg:block sticky top-0 h-fit pt-2">
                            <p class="text-[10px] font-black text-neutral-600 uppercase tracking-[0.2em] mb-6">Contents</p>
                            <nav id="toc-list" class="space-y-3 text-[10px] border-l border-[#333]"></nav>
                        </div>

                        <!-- 原始 JSON 视图 -->
                        <div id="view-raw" class="hidden flex-1">
                            <div class="bg-[#0c0c0c] border border-[#333] rounded-lg p-8 overflow-x-auto shadow-2xl text-xs custom-scrollbar">
                                <pre><code class="language-json" id="raw-json-code"></code></pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script id="interaction-data" type="application/json">DATA_PLACEHOLDER</script>
    <script>
        const data = JSON.parse(document.getElementById('interaction-data').textContent);
        
        let lastMtime = null;
        async function checkUpdate() {
            try {
                const res = await fetch('/report/status');
                if (!res.ok) return;
                const status = await res.json();
                if (lastMtime !== null && status.mtime > lastMtime) {
                    window.location.reload();
                }
                lastMtime = status.mtime;
            } catch (e) {}
        }
        setInterval(checkUpdate, 2000);

        function init() {
            const listContainer = document.getElementById('prompt-list');
            const summaryInfo = document.getElementById('summary-info');
            summaryInfo.textContent = `${data.total_prompts} RECORDS / UPDATED ${new Date(data.last_updated).toLocaleTimeString()}`;
            const prompts = [...data.prompts].reverse();
            prompts.forEach((item, index) => {
                const actualIndex = data.prompts.length - 1 - index;
                const div = document.createElement('div');
                div.className = 'p-5 border-b border-[#222] hover:bg-[#1a1a1a] cursor-pointer transition-all border-l-4 border-l-transparent group';
                div.id = `item-${actualIndex}`;
                div.onclick = () => showDetail(actualIndex);
                let preview = "No message content";
                if (item.full_request.messages && item.full_request.messages.length > 0) {
                    const lastMsg = item.full_request.messages[item.full_request.messages.length - 1];
                    if (Array.isArray(lastMsg.content)) {
                        const textObj = lastMsg.content.find(c => c.type === 'text');
                        preview = textObj ? textObj.text.substring(0, 60) : preview;
                    } else if (typeof lastMsg.content === 'string') {
                        preview = lastMsg.content.substring(0, 60);
                    }
                }
                div.innerHTML = `
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-[10px] font-black text-amber-600 uppercase tracking-widest">${item.model}</span>
                        <span class="text-[9px] font-mono text-neutral-600 group-hover:text-neutral-400 transition-colors">${item.timestamp.split(' ')[1]}</span>
                    </div>
                    <div class="text-[11px] text-neutral-500 line-clamp-2 leading-relaxed font-medium">${preview}</div>
                `;
                listContainer.appendChild(div);
            });
        }

        function toggleTool(id) {
            const content = document.getElementById(`content-${id}`);
            const icon = document.getElementById(`icon-${id}`);
            const isHidden = content.classList.contains('hidden');
            if (isHidden) {
                content.classList.remove('hidden');
                icon.style.transform = 'rotate(180deg)';
            } else {
                content.classList.add('hidden');
                icon.style.transform = 'rotate(0deg)';
            }
        }

        function showDetail(index) {
            const item = data.prompts[index];
            document.getElementById('welcome-message').classList.add('hidden');
            document.getElementById('content-area').classList.remove('hidden');
            switchTab('render');
            const scrollContainer = document.getElementById('scroll-container');
            scrollContainer.scrollTop = 0;
            document.querySelectorAll('#prompt-list > div').forEach(el => el.classList.remove('bg-[#262626]', 'border-l-amber-600'));
            document.getElementById(`item-${index}`).classList.add('bg-[#262626]', 'border-l-amber-600');
            document.getElementById('detail-model').textContent = item.model.toUpperCase();
            document.getElementById('detail-time').textContent = item.timestamp;
            const userId = item.full_request.metadata ? item.full_request.metadata.user_id : 'anonymous';
            document.getElementById('detail-user-id').textContent = userId;
            document.getElementById('badge-stream').style.display = item.full_request.stream ? 'inline-block' : 'none';
            const tocList = document.getElementById('toc-list');
            tocList.innerHTML = '';
            const addTocItem = (id, text, level = 0) => {
                const a = document.createElement('a');
                a.href = `#${id}`;
                a.className = `block py-1 px-4 border-l-2 border-transparent hover:text-amber-600 transition-all uppercase tracking-widest font-black ${level > 0 ? 'pl-8 text-[9px] text-neutral-600' : 'text-[10px] text-neutral-400'}`;
                a.textContent = text;
                a.id = `toc-link-${id}`;
                a.onclick = (e) => {
                    e.preventDefault();
                    document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
                    if (id.startsWith('tool-')) {
                        const content = document.getElementById(`content-${id}`);
                        if (content && content.classList.contains('hidden')) toggleTool(id);
                    }
                };
                tocList.appendChild(a);
            };

            addTocItem('section-system', 'System Directives');
            const systemContainer = document.getElementById('system-container');
            systemContainer.innerHTML = '';
            const systems = Array.isArray(item.full_request.system) ? item.full_request.system : [item.full_request.system];
            systems.filter(s => s).forEach(s => {
                const text = typeof s === 'string' ? s : (s.text || JSON.stringify(s));
                const div = document.createElement('div');
                div.className = 'p-6 rounded-lg text-sm message-system markdown-body';
                div.innerHTML = marked.parse(text);
                systemContainer.appendChild(div);
            });

            addTocItem('section-messages', 'Interaction Log');
            const msgContainer = document.getElementById('messages-container');
            msgContainer.innerHTML = '';
            item.full_request.messages.forEach((msg, mIdx) => {
                const msgId = `msg-${mIdx}`;
                const div = document.createElement('div');
                div.id = msgId;
                const isUser = msg.role === 'user';
                div.className = `p-6 rounded-lg ${isUser ? 'message-user' : 'message-assistant'}`;
                let contentHtml = '';
                const processText = (text) => {
                    if (!text) return '';
                    const reminderRegex = /<system-reminder>([\s\S]*?)<\/system-reminder>/g;
                    let processedText = text.replace(reminderRegex, '');
                    let html = marked.parse(processedText);
                    let match;
                    while ((match = reminderRegex.exec(text)) !== null) {
                        html += `
                            <div class="mt-6 border border-amber-900/40 bg-amber-950/20 rounded-lg overflow-hidden">
                                <div class="bg-amber-950/40 px-3 py-1.5 flex items-center gap-2 border-b border-amber-900/20">
                                    <svg class="w-3 h-3 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
                                    <span class="text-[8px] font-black text-amber-600 uppercase tracking-widest">System Warning</span>
                                </div>
                                <div class="p-5 text-[13px] text-amber-200/70 markdown-body bg-transparent">${marked.parse(match[1])}</div>
                            </div>`;
                    }
                    return html;
                };
                if (Array.isArray(msg.content)) {
                    contentHtml = '<div class="space-y-6">';
                    msg.content.forEach(c => {
                        contentHtml += '<div class="content-block pb-6 last:pb-0 last:border-0 border-b border-[#333]">';
                        if (c.type === 'text') contentHtml += processText(c.text);
                        else if (c.type === 'tool_use') contentHtml += `<div class="bg-black text-amber-500 p-3 rounded font-mono text-[10px] uppercase tracking-[0.2em] border border-amber-900/30">Execute: ${c.name}</div>`;
                        else if (c.type === 'tool_result') contentHtml += `<div class="bg-[#111] text-blue-400 p-3 rounded font-mono text-[10px] uppercase tracking-[0.2em] border border-blue-900/30">Output Captured</div>`;
                        contentHtml += '</div>';
                    });
                    contentHtml += '</div>';
                } else {
                    contentHtml = processText(msg.content || '');
                }
                div.innerHTML = `
                    <div class="flex items-center justify-between mb-4 border-b border-[#333] pb-2">
                        <span class="text-[9px] font-black uppercase tracking-[0.2em] ${isUser ? 'text-blue-500' : 'text-amber-500'}">${msg.role}</span>
                    </div>
                    <div class="text-sm markdown-body">${contentHtml}</div>`;
                msgContainer.appendChild(div);
                addTocItem(msgId, `${msg.role.toUpperCase()} INPUT`, 1);
            });

            addTocItem('section-response', 'Final Response');
            const responseContainer = document.getElementById('response-container');
            const thinkingContainer = document.getElementById('thinking-container');
            const thinkingContent = document.getElementById('thinking-content');
            responseContainer.innerHTML = '';
            thinkingContainer.classList.add('hidden');
            thinkingContent.innerHTML = '';
            if (item.full_response) {
                let responseText = '', thinkingText = '';
                if (item.full_response.raw_stream) {
                    const lines = item.full_response.raw_stream.split('\n');
                    let accText = '', accThink = '';
                    lines.forEach(line => {
                        if (line.startsWith('data: ')) {
                            try {
                                const d = JSON.parse(line.substring(6));
                                if (d.type === 'content_block_delta' && d.delta) {
                                    if (d.delta.text) accText += d.delta.text;
                                    if (d.delta.thinking) accThink += d.delta.thinking;
                                } else if (d.type === 'content_block_start' && d.content_block) {
                                    if (d.content_block.thinking) accThink += d.content_block.thinking;
                                } else if (d.choices?.[0]?.delta) {
                                    const del = d.choices[0].delta;
                                    if (del.content) accText += del.content;
                                    if (del.reasoning_content) accThink += del.reasoning_content;
                                }
                            } catch (e) {}
                        }
                    });
                    responseText = accText; thinkingText = accThink;
                    if (!responseText && !thinkingText) responseText = '_No readable content found in stream._';
                } else if (typeof item.full_response === 'object') {
                    if (item.full_response.content && Array.isArray(item.full_response.content)) {
                        item.full_response.content.forEach(c => {
                            if (c.type === 'text') responseText += (c.text || '');
                            if (c.type === 'thinking') thinkingText += (c.thinking || '');
                        });
                    } else if (item.full_response.choices?.[0]?.message) {
                        const m = item.full_response.choices[0].message;
                        responseText = m.content || '';
                        thinkingText = m.reasoning_content || '';
                    } else responseText = JSON.stringify(item.full_response, null, 2);
                } else responseText = String(item.full_response);
                if (thinkingText) {
                    thinkingContainer.classList.remove('hidden');
                    thinkingContent.innerHTML = marked.parse(thinkingText);
                }
                const div = document.createElement('div');
                div.className = 'p-8 rounded-lg message-assistant markdown-body border border-amber-900/30 bg-[#262626] shadow-2xl';
                div.innerHTML = marked.parse(responseText || '*Empty output*');
                responseContainer.appendChild(div);
            } else responseContainer.innerHTML = '<p class="text-neutral-600 italic text-sm font-mono">// no response captured</p>';

            const toolsSection = document.getElementById('tools-section');
            const toolsContainer = document.getElementById('tools-container');
            if (item.full_request.tools?.length > 0) {
                toolsSection.classList.remove('hidden');
                addTocItem('tools-section', 'Tool Definitions');
                toolsContainer.innerHTML = '';
                item.full_request.tools.forEach((tool, tIdx) => {
                    const toolCardId = `tool-${tIdx}`;
                    const div = document.createElement('div');
                    div.id = toolCardId;
                    div.className = 'border border-[#333] bg-[#1a1a1a] rounded-lg overflow-hidden mb-6 shadow-lg';
                    let propertiesHtml = '';
                    if (tool.input_schema?.properties) {
                        const req = tool.input_schema.required || [];
                        propertiesHtml = '<div class="bg-black/20 border-t border-[#333] p-5"><p class="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-4">Schema Definition</p><div class="space-y-4">';
                        for (const [name, prop] of Object.entries(tool.input_schema.properties)) {
                            propertiesHtml += `
                                <div class="flex flex-col sm:flex-row gap-6 border-b border-[#222] pb-4 last:border-0 last:pb-0">
                                    <div class="min-w-[160px] flex items-center gap-2">
                                        <code class="text-amber-500 font-bold text-xs font-mono">${name}</code>
                                        ${req.includes(name) ? '<span class="text-[7px] font-black bg-amber-900/40 text-amber-500 px-1.5 py-0.5 rounded uppercase tracking-tighter">Required</span>' : ''}
                                    </div>
                                    <div class="flex-1">
                                        <span class="text-[9px] bg-[#333] text-neutral-400 px-2 py-0.5 rounded font-mono">${prop.type || 'any'}</span>
                                        <p class="text-xs text-neutral-500 mt-2 leading-relaxed">${prop.description || ''}</p>
                                    </div>
                                </div>`;
                        }
                        propertiesHtml += '</div></div>';
                    }
                    div.innerHTML = `
                        <div class="p-5 cursor-pointer hover:bg-[#222] flex items-center justify-between transition-colors" onclick="toggleTool('${toolCardId}')">
                            <div class="flex items-center gap-4">
                                <div class="p-2 bg-amber-600/10 text-amber-600 rounded border border-amber-600/20"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" stroke-width="2"></path></svg></div>
                                <h4 class="text-sm font-black font-mono tracking-tight text-white">${tool.name}</h4>
                            </div>
                            <svg id="icon-${toolCardId}" class="w-4 h-4 text-[#444] transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" stroke-width="2"></path></svg>
                        </div>
                        <div id="content-${toolCardId}" class="hidden border-t border-[#333]">
                            <div class="p-6 text-[13px] markdown-body leading-relaxed">${marked.parse(tool.description || '')}</div>
                            ${propertiesHtml}
                        </div>`;
                    toolsContainer.appendChild(div);
                    addTocItem(toolCardId, tool.name, 1);
                });
            } else toolsSection.classList.add('hidden');

            document.getElementById('raw-json-code').textContent = JSON.stringify(item, null, 2);
            Prism.highlightAll();
        }

        function switchTab(view) {
            const render = document.getElementById('view-render'), raw = document.getElementById('view-raw');
            const rBtn = document.getElementById('tab-render'), rwBtn = document.getElementById('tab-raw');
            const toc = document.getElementById('toc-container');
            if (view === 'render') {
                render.classList.remove('hidden'); raw.classList.add('hidden'); toc?.classList.remove('invisible');
                rBtn.className = 'pb-2 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2 border-amber-600 text-white';
                rwBtn.className = 'pb-2 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2 border-transparent text-neutral-500 hover:text-neutral-300';
            } else {
                render.classList.add('hidden'); raw.classList.remove('hidden'); toc?.classList.add('invisible');
                rBtn.className = 'pb-2 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2 border-transparent text-neutral-500 hover:text-neutral-300';
                rwBtn.className = 'pb-2 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2 border-amber-600 text-white';
            }
        }
        init();
    </script>
</body>
</html>"""

def generate_report(input_file: Path, output_file: Path):
    if not input_file.exists():
        return

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to read/parse {input_file}: {e}")
        return

    # Processing ...
    json_data = json.dumps(data, ensure_ascii=False)
    json_data = json_data.replace("</script>", "<\\/script>")
    html_content = HTML_TEMPLATE.replace("DATA_PLACEHOLDER", json_data)
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.debug(f"Report generated: {output_file}")
    except Exception as e:
        logger.error(f"Failed to write report {output_file}: {e}")

def main():
    logging.basicConfig(level=logging.INFO)
    # Default paths for CLI usage
    base_dir = Path.cwd()
    input_path = base_dir / "data" / "ai_prompts.json"
    output_path = base_dir / "data" / "prompt_report.html"
    generate_report(input_path, output_path)

if __name__ == "__main__":
    main()
