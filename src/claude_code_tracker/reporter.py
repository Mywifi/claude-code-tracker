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
    <title>AI 提示词分析报告</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <style>
        .markdown-body { background-color: transparent !important; font-size: 14px; }
        .markdown-body pre { background-color: #1f2937 !important; padding: 1rem; border-radius: 0.5rem; color: #f3f4f6; overflow-x: auto; border: none; }
        .markdown-body code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; background-color: rgba(175, 184, 193, 0.2); padding: 0.2em 0.4em; border-radius: 6px; }
        .markdown-body pre code { background-color: transparent; padding: 0; }
        .message-user { 
            background-color: #f8fafc; 
            border: 1px solid #e2e8f0;
            border-left: 4px solid #3b82f6;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .message-assistant { 
            background-color: #ffffff; 
            border: 1px solid #e2e8f0;
            border-left: 4px solid #10b981;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .message-system { 
            background-color: #fffaf0; 
            border: 1px solid #feebc8;
            border-left: 4px solid #f59e0b;
        }
        .message-user:hover, .message-assistant:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.2s ease;
        }
    </style>
</head>
<body class="bg-gray-100 min-h-screen font-sans">
    <div class="max-w-[1400px] mx-auto bg-white shadow-2xl flex h-screen overflow-hidden border-x border-gray-200">
        <!-- 侧边栏 -->
        <div class="w-80 border-r border-gray-200 flex flex-col bg-gray-50">
            <div class="p-4 border-b border-gray-200 bg-blue-600 text-white shadow-md">
                <h1 class="text-xl font-bold">Claude Tracker</h1>
                <p class="text-xs opacity-80 mt-1" id="summary-info">加载中...</p>
            </div>
            <div class="flex-1 overflow-y-auto" id="prompt-list">
                <!-- 列表项将在这里动态生成 -->
            </div>
        </div>

        <!-- 主内容区 -->
        <div class="flex-1 bg-white flex flex-col" id="detail-view">
            <div id="welcome-message" class="flex flex-col items-center justify-center h-full text-gray-400">
                <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path>
                </svg>
                <p class="text-xl">请从左侧选择一条消息进行分析</p>
            </div>
            <div id="content-area" class="hidden flex-1 flex flex-col overflow-hidden">
                <div class="bg-white z-20 px-8 pt-8 pb-4 border-b border-gray-100 shadow-sm">
                    <div class="max-w-5xl mx-auto">
                        <div class="flex justify-between items-start">
                            <div>
                                <h2 class="text-2xl font-bold text-gray-800" id="detail-model">模型名称</h2>
                                <div class="flex items-center gap-4 mt-1">
                                    <p class="text-gray-500 text-sm" id="detail-time">时间戳</p>
                                    <span class="text-gray-300">|</span>
                                    <p class="text-blue-600 text-sm font-mono" id="detail-user-id">User ID</p>
                                </div>
                            </div>
                            <div class="flex gap-2">
                                <span id="badge-stream" class="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 uppercase tracking-wider">Stream</span>
                            </div>
                        </div>

                        <!-- Tab 切换 -->
                        <div class="flex gap-1 mt-6 bg-gray-100 p-1 rounded-lg w-fit">
                            <button onclick="switchTab('render')" id="tab-render" class="px-4 py-1.5 rounded-md text-sm font-medium transition-all bg-white shadow-sm text-blue-600">
                                渲染视图
                            </button>
                            <button onclick="switchTab('raw')" id="tab-raw" class="px-4 py-1.5 rounded-md text-sm font-medium transition-all text-gray-500 hover:text-gray-700">
                                原始 JSON
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 可滚动的内容区域 -->
                <div class="flex-1 overflow-y-auto p-8 relative scroll-smooth" id="scroll-container">
                    <div class="max-w-5xl mx-auto pb-20 flex gap-8">
                        <div id="view-render" class="flex-1 space-y-8 min-w-0">
                            <!-- 系统提示词 -->
                            <div id="section-system">
                                <h3 class="text-lg font-semibold mb-3 flex items-center">
                                    <span class="w-2 h-6 bg-orange-500 rounded-full mr-2"></span>
                                    System Prompts
                                </h3>
                                <div id="system-container" class="space-y-3"></div>
                            </div>

                            <!-- 对话内容 -->
                            <div id="section-messages">
                                <h3 class="text-lg font-semibold mb-3 flex items-center">
                                    <span class="w-2 h-6 bg-blue-500 rounded-full mr-2"></span>
                                    Messages
                                </h3>
                                <div id="messages-container" class="space-y-8"></div>
                            </div>

                            <!-- AI 响应内容 -->
                            <div id="section-response">
                                <h3 class="text-lg font-semibold mb-3 flex items-center">
                                    <span class="w-2 h-6 bg-green-500 rounded-full mr-2"></span>
                                    AI Response
                                </h3>
                                <div id="thinking-container" class="mb-4 hidden">
                                    <div class="border-l-4 border-amber-300 bg-amber-50 rounded-r-lg overflow-hidden shadow-sm">
                                        <div class="bg-amber-100 px-3 py-1.5 flex items-center gap-2">
                                            <svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                                            </svg>
                                            <span class="text-[10px] font-black text-amber-800 uppercase tracking-widest">Thinking Process</span>
                                        </div>
                                        <div id="thinking-content" class="p-4 text-sm text-amber-900 markdown-body bg-transparent italic"></div>
                                    </div>
                                </div>
                                <div id="response-container" class="space-y-3"></div>
                            </div>

                            <!-- 工具定义 -->
                            <div class="hidden" id="tools-section">
                                <h3 class="text-lg font-semibold mb-3 flex items-center">
                                    <span class="w-2 h-6 bg-purple-500 rounded-full mr-2"></span>
                                    Available Tools
                                </h3>
                                <div id="tools-container" class="space-y-4 text-sm"></div>
                            </div>
                        </div>

                        <!-- 目录 TOC -->
                        <div id="toc-container" class="w-48 shrink-0 hidden lg:block sticky top-0 h-fit pt-2">
                            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-4">On This Page</p>
                            <nav id="toc-list" class="space-y-1 text-sm border-l border-gray-100"></nav>
                        </div>

                        <!-- 原始 JSON 视图 -->
                        <div id="view-raw" class="hidden flex-1">
                            <div class="bg-gray-900 rounded-xl p-6 overflow-x-auto shadow-inner text-sm">
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
            summaryInfo.textContent = `共 ${data.total_prompts} 条记录 | ${new Date(data.last_updated).toLocaleString()}`;
            const prompts = [...data.prompts].reverse();
            prompts.forEach((item, index) => {
                const actualIndex = data.prompts.length - 1 - index;
                const div = document.createElement('div');
                div.className = 'p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors border-l-4 border-l-transparent';
                div.id = `item-${actualIndex}`;
                div.onclick = () => showDetail(actualIndex);
                let preview = "No message content";
                if (item.full_request.messages && item.full_request.messages.length > 0) {
                    const lastMsg = item.full_request.messages[item.full_request.messages.length - 1];
                    if (Array.isArray(lastMsg.content)) {
                        const textObj = lastMsg.content.find(c => c.type === 'text');
                        preview = textObj ? textObj.text.substring(0, 60) + '...' : preview;
                    } else if (typeof lastMsg.content === 'string') {
                        preview = lastMsg.content.substring(0, 60) + '...';
                    }
                }
                div.innerHTML = `
                    <div class="flex justify-between mb-1">
                        <span class="font-semibold text-sm text-blue-600">${item.model}</span>
                        <span class="text-xs text-gray-400">${item.timestamp.split(' ')[1]}</span>
                    </div>
                    <div class="text-xs text-gray-600 line-clamp-2">${preview}</div>
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
            document.querySelectorAll('#prompt-list > div').forEach(el => el.classList.remove('bg-blue-50', 'border-l-blue-500'));
            document.getElementById(`item-${index}`).classList.add('bg-blue-50', 'border-l-blue-500');
            document.getElementById('detail-model').textContent = item.model;
            document.getElementById('detail-time').textContent = item.timestamp;
            const userId = item.full_request.metadata ? item.full_request.metadata.user_id : 'Unknown User';
            document.getElementById('detail-user-id').textContent = `User: ${userId}`;
            document.getElementById('badge-stream').style.display = item.full_request.stream ? 'inline-block' : 'none';
            const tocList = document.getElementById('toc-list');
            tocList.innerHTML = '';
            const addTocItem = (id, text, level = 0) => {
                const a = document.createElement('a');
                a.href = `#${id}`;
                a.className = `block py-1 px-4 border-l-2 border-transparent hover:text-blue-600 transition-all ${level > 0 ? 'pl-8 text-xs' : 'font-medium text-gray-600'}`;
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

            addTocItem('section-system', 'System Prompts');
            const systemContainer = document.getElementById('system-container');
            systemContainer.innerHTML = '';
            const systems = Array.isArray(item.full_request.system) ? item.full_request.system : [item.full_request.system];
            systems.filter(s => s).forEach(s => {
                const text = typeof s === 'string' ? s : (s.text || JSON.stringify(s));
                const div = document.createElement('div');
                div.className = 'p-4 rounded-lg text-sm text-gray-700 message-system markdown-body';
                div.innerHTML = marked.parse(text);
                systemContainer.appendChild(div);
            });

            addTocItem('section-messages', 'Messages');
            const msgContainer = document.getElementById('messages-container');
            msgContainer.innerHTML = '';
            item.full_request.messages.forEach((msg, mIdx) => {
                const msgId = `msg-${mIdx}`;
                const div = document.createElement('div');
                div.id = msgId;
                const isUser = msg.role === 'user';
                div.className = `p-4 rounded-lg ${isUser ? 'message-user' : 'message-assistant'}`;
                let contentHtml = '';
                const processText = (text) => {
                    if (!text) return '';
                    const reminderRegex = /<system-reminder>([\s\S]*?)<\/system-reminder>/g;
                    let processedText = text.replace(reminderRegex, '');
                    let html = marked.parse(processedText);
                    let match;
                    while ((match = reminderRegex.exec(text)) !== null) {
                        html += `
                            <div class="mt-4 border-2 border-amber-200 bg-amber-50 rounded-lg overflow-hidden shadow-sm">
                                <div class="bg-amber-200 px-3 py-1 flex items-center gap-2">
                                    <svg class="w-4 h-4 text-amber-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
                                    <span class="text-[10px] font-black text-amber-800 uppercase tracking-widest">System Reminder</span>
                                </div>
                                <div class="p-4 text-sm text-amber-900 markdown-body bg-transparent">${marked.parse(match[1])}</div>
                            </div>`;
                    }
                    return html;
                };
                if (Array.isArray(msg.content)) {
                    contentHtml = '<div class="space-y-6">';
                    msg.content.forEach(c => {
                        contentHtml += '<div class="content-block pb-6 last:pb-0 last:border-0 border-b border-gray-200">';
                        if (c.type === 'text') contentHtml += processText(c.text);
                        else if (c.type === 'tool_use') contentHtml += `<div class="bg-black text-green-400 p-2 rounded text-xs font-mono uppercase tracking-widest font-bold px-3 py-1">Tool Use: ${c.name}</div>`;
                        else if (c.type === 'tool_result') contentHtml += `<div class="bg-gray-800 text-blue-300 p-2 rounded text-xs font-mono uppercase tracking-widest font-bold px-3 py-1">Tool Result</div>`;
                        contentHtml += '</div>';
                    });
                    contentHtml += '</div>';
                } else {
                    contentHtml = processText(msg.content || '');
                }
                div.innerHTML = `
                    <div class="flex items-center mb-2 border-b border-gray-200 border-opacity-20 pb-1">
                        <span class="text-[10px] font-black uppercase tracking-widest ${isUser ? 'text-blue-600' : 'text-green-600'}">${msg.role}</span>
                    </div>
                    <div class="text-sm text-gray-800 markdown-body">${contentHtml}</div>`;
                msgContainer.appendChild(div);
                let preview = msg.role;
                if (msg.content) {
                    const text = Array.isArray(msg.content) ? (msg.content.find(c => c.type === 'text')?.text || '') : msg.content;
                    if (text) preview += `: ${text.substring(0, 15)}...`;
                }
                addTocItem(msgId, preview, 1);
            });

            addTocItem('section-response', 'AI Response');
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
                    if (!responseText && !thinkingText) responseText = '无法从流中提取内容，请查看原始 JSON。';
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
                div.className = 'p-4 rounded-lg message-assistant markdown-body border-2 border-green-100 shadow-sm';
                div.innerHTML = marked.parse(responseText || '*无正文回复*');
                responseContainer.appendChild(div);
            } else responseContainer.innerHTML = '<p class="text-gray-400 italic text-sm">无响应内容。</p>';

            const toolsSection = document.getElementById('tools-section');
            const toolsContainer = document.getElementById('tools-container');
            if (item.full_request.tools?.length > 0) {
                toolsSection.classList.remove('hidden');
                addTocItem('tools-section', 'Available Tools');
                toolsContainer.innerHTML = '';
                item.full_request.tools.forEach((tool, tIdx) => {
                    const toolCardId = `tool-${tIdx}`;
                    const div = document.createElement('div');
                    div.id = toolCardId;
                    div.className = 'border border-purple-200 bg-purple-50 rounded-xl shadow-sm overflow-hidden mb-4';
                    let propertiesHtml = '';
                    if (tool.input_schema?.properties) {
                        const req = tool.input_schema.required || [];
                        propertiesHtml = '<div class="bg-white bg-opacity-50 border-t border-purple-100 p-4"><p class="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-3">Parameters</p><div class="space-y-3">';
                        for (const [name, prop] of Object.entries(tool.input_schema.properties)) {
                            propertiesHtml += `
                                <div class="flex flex-col sm:flex-row gap-4 border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                                    <div class="min-w-[140px] flex items-center gap-2">
                                        <code class="text-purple-700 font-bold text-sm bg-purple-50 px-1.5 py-0.5 rounded">${name}</code>
                                        ${req.includes(name) ? '<span class="text-[8px] font-bold bg-red-100 text-red-600 px-1 rounded">REQ</span>' : ''}
                                    </div>
                                    <div class="flex-1">
                                        <span class="text-[10px] bg-gray-200 px-1 rounded">${prop.type || 'any'}</span>
                                        <p class="text-xs text-gray-600 mt-1">${prop.description || ''}</p>
                                    </div>
                                </div>`;
                        }
                        propertiesHtml += '</div></div>';
                    }
                    div.innerHTML = `
                        <div class="p-4 cursor-pointer hover:bg-purple-100 flex items-center justify-between" onclick="toggleTool('${toolCardId}')">
                            <div class="flex items-center gap-3">
                                <div class="p-2 bg-purple-600 text-white rounded-lg"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" stroke-width="2"></path></svg></div>
                                <h4 class="text-base font-bold font-mono">${tool.name}</h4>
                            </div>
                            <svg id="icon-${toolCardId}" class="w-5 h-5 text-purple-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" stroke-width="2"></path></svg>
                        </div>
                        <div id="content-${toolCardId}" class="hidden border-t border-purple-100">
                            <div class="p-5 text-sm markdown-body">${marked.parse(tool.description || '')}</div>
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
                rBtn.className = 'px-4 py-1.5 rounded-md text-sm font-medium bg-white shadow-sm text-blue-600';
                rwBtn.className = 'px-4 py-1.5 rounded-md text-sm font-medium text-gray-500';
            } else {
                render.classList.add('hidden'); raw.classList.remove('hidden'); toc?.classList.add('invisible');
                rBtn.className = 'px-4 py-1.5 rounded-md text-sm font-medium text-gray-500';
                rwBtn.className = 'px-4 py-1.5 rounded-md text-sm font-medium bg-white shadow-sm text-blue-600';
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
