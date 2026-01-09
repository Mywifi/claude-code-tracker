let appData = null;
let lastMtime = null;
let currentDetailIndex = null;
let currentTab = 'render';

// Theme management
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

function setTheme(theme) {
    const html = document.documentElement;
    html.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateThemeIcons(theme);
}

function updateThemeIcons(theme) {
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');
    if (theme === 'light') {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    } else {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const defaultTheme = savedTheme || (prefersDark ? 'dark' : 'light');
    setTheme(defaultTheme);
}

// Data fetching
async function fetchData() {
    try {
        const res = await fetch('/report/data');
        if (!res.ok) return;
        appData = await res.json();
        renderPromptList();
        updateSummary();
        if (currentDetailIndex !== null) {
            showDetail(currentDetailIndex, false);  // Don't reset scroll on data refresh
        }
    } catch (e) {
        console.error("Failed to fetch data:", e);
    }
}

async function checkUpdate() {
    try {
        const res = await fetch('/report/status');
        if (!res.ok) return;
        const status = await res.json();
        if (lastMtime !== null && status.mtime > lastMtime) {
            await fetchData();
        }
        lastMtime = status.mtime;
    } catch (e) {}
}

// UI Rendering
function updateSummary() {
    const summaryInfo = document.getElementById('summary-info');
    if (appData) {
        const time = new Date(appData.last_updated).toLocaleTimeString();
        summaryInfo.textContent = `${appData.total_prompts} RECORDS / UPDATED ${time}`;
    }
}

function renderPromptList() {
    const listContainer = document.getElementById('prompt-list');
    listContainer.innerHTML = '';

    if (!appData || !appData.prompts) return;

    // Create a map of item to its original index for quick lookup
    const indexMap = new Map();
    appData.prompts.forEach((item, idx) => {
        // Use a combination of timestamp and model as key
        const key = `${item.timestamp}-${item.model}`;
        indexMap.set(item, idx);
    });

    // Sort by updated_at descending, fallback to timestamp
    const sortedPrompts = [...appData.prompts].sort((a, b) => {
        const timeA = a.updated_at || a.timestamp;
        const timeB = b.updated_at || b.timestamp;
        // Direct string comparison works for "YYYY-MM-DD HH:MM:SS,mmm" format
        return timeB.localeCompare(timeA);
    });

    sortedPrompts.forEach((item) => {
        // Get original index from the map
        const actualIndex = indexMap.get(item);
        const div = document.createElement('div');
        div.className = `p-5 list-item cursor-pointer border-l-4 border-l-transparent group ${currentDetailIndex === actualIndex ? 'active' : ''}`;
        div.id = `item-${actualIndex}`;
        div.onclick = () => showDetail(actualIndex);

        let preview = item.first_user_message || "No message content";
        if (!item.first_user_message && item.full_request.messages && item.full_request.messages.length > 0) {
            const lastMsg = item.full_request.messages[item.full_request.messages.length - 1];
            if (Array.isArray(lastMsg.content)) {
                const textObj = lastMsg.content.find(c => c.type === 'text');
                preview = textObj ? textObj.text.substring(0, 60) : preview;
            } else if (typeof lastMsg.content === 'string') {
                preview = lastMsg.content.substring(0, 60);
            }
        }

        const displayTime = (item.updated_at || item.timestamp).split(' ')[1] || (item.updated_at || item.timestamp).split('T')[1]?.split('.')[0] || "";

        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="text-[10px] font-black text-amber-600 uppercase tracking-widest">${item.model}</span>
                <span class="text-[9px] font-mono text-neutral-600 group-hover:text-neutral-400 transition-colors">${displayTime}</span>
            </div>
            <div class="text-[11px] text-neutral-500 line-clamp-2 leading-relaxed font-medium">${preview}</div>
        `;
        listContainer.appendChild(div);
    });
}

function showDetail(index, resetScroll = true) {
    currentDetailIndex = index;
    const item = appData.prompts[index];
    
    document.getElementById('welcome-message').classList.add('hidden');
    document.getElementById('content-area').classList.remove('hidden');
    
    // Highlight active list item
    document.querySelectorAll('#prompt-list > div').forEach(el => el.classList.remove('active'));
    const activeItem = document.getElementById(`item-${index}`);
    if (activeItem) activeItem.classList.add('active');
    
    document.getElementById('detail-model').textContent = item.model.toUpperCase();
    
    const timeDisplay = item.updated_at ? `STARTED: ${item.timestamp} / UPDATED: ${item.updated_at}` : item.timestamp;
    document.getElementById('detail-time').textContent = timeDisplay;
    const userId = item.full_request.metadata ? item.full_request.metadata.user_id : 'anonymous';
    document.getElementById('detail-user-id').textContent = userId;
    document.getElementById('badge-stream').style.display = item.full_request.stream ? 'inline-block' : 'none';
    
    renderTabs(item);
    renderSystemDirectives(item);
    renderInteractionLog(item);
    renderFinalResponse(item);
    renderToolDefinitions(item);
    updateTOC();
    
    switchTab(currentTab);
    
    // Only reset scroll when user clicks (not on data refresh)
    if (resetScroll) {
        document.getElementById('scroll-container').scrollTop = 0;
    }
    
    // Highlight code
    if (typeof Prism !== 'undefined') {
        Prism.highlightAll();
    }
}

function renderSystemDirectives(item) {
    const container = document.getElementById('system-container');
    container.innerHTML = '';
    const systems = Array.isArray(item.full_request.system) ? item.full_request.system : [item.full_request.system];
    systems.filter(s => s).forEach(s => {
        const text = typeof s === 'string' ? s : (s.text || JSON.stringify(s));
        const div = document.createElement('div');
        div.className = 'p-6 rounded-lg text-sm message-system markdown-body';
        div.innerHTML = marked.parse(text);
        container.appendChild(div);
    });
}

function processText(text) {
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
                    <span class="text-[8px] font-black text-amber-600 uppercase tracking-widest">system-reminder</span>
                </div>
                <div class="p-5 text-[13px] text-amber-200/70 markdown-body bg-transparent">${marked.parse(match[1])}</div>
            </div>`;
    }
    return html;
}

function renderInteractionLog(item) {
    const container = document.getElementById('messages-container');
    container.innerHTML = '';
    item.full_request.messages.forEach((msg, mIdx) => {
        const div = document.createElement('div');
        div.id = `msg-${mIdx}`;
        const isUser = msg.role === 'user';
        div.className = `p-6 rounded-lg ${isUser ? 'message-user' : 'message-assistant'}`;

        let contentHtml = '';
        if (Array.isArray(msg.content)) {
            contentHtml = '<div class="space-y-6">';
            msg.content.forEach(c => {
                contentHtml += '<div class="content-block pb-6 last:pb-0 last:border-0 border-b border-claude last:border-0">';

                if (c.type === 'text') {
                    contentHtml += processText(c.text);
                }
                else if (c.type === 'thinking') {
                    // Thinking content block
                    contentHtml += `
                        <div class="bg-amber-900/10 border border-amber-900/30 rounded-lg overflow-hidden">
                            <div class="bg-amber-900/20 px-3 py-1.5 flex items-center gap-2 border-b border-amber-900/20">
                                <svg class="w-3 h-3 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                                </svg>
                                <span class="text-[9px] font-black text-amber-500 uppercase tracking-[0.2em]">Thinking</span>
                            </div>
                            <div class="p-3 text-sm text-amber-500/80 italic">${c.thinking || ''}</div>
                        </div>`;
                }
                else if (c.type === 'tool_use') {
                    // Tool execution block
                    const toolInput = c.input ? JSON.stringify(c.input, null, 2) : '';
                    contentHtml += `
                        <div class="bg-claude-card border border-amber-600/30 rounded-lg overflow-hidden">
                            <div class="bg-amber-600/10 px-3 py-1.5 flex items-center gap-2 border-b border-amber-600/20">
                                <svg class="w-3 h-3 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                </svg>
                                <span class="text-[9px] font-black text-amber-500 uppercase tracking-[0.2em]">Execute: ${c.name}</span>
                            </div>
                            ${toolInput ? `<div class="p-3"><pre class="text-xs text-claude-text-muted overflow-x-auto"><code>${escapeHtml(toolInput)}</code></pre></div>` : ''}
                        </div>`;
                }
                else if (c.type === 'tool_result') {
                    // Tool result block
                    let resultContent = '';
                    if (typeof c.content === 'string') {
                        resultContent = c.content;
                    } else if (Array.isArray(c.content)) {
                        resultContent = c.content.map(item => item.text || JSON.stringify(item)).join('\n');
                    } else if (c.content) {
                        resultContent = JSON.stringify(c.content, null, 2);
                    }

                    // Truncate long outputs
                    if (resultContent.length > 2000) {
                        resultContent = resultContent.substring(0, 2000) + '\n\n... (truncated)';
                    }

                    contentHtml += `
                        <div class="bg-claude-card border border-blue-600/30 rounded-lg overflow-hidden">
                            <div class="bg-blue-600/10 px-3 py-1.5 flex items-center gap-2 border-b border-blue-600/20">
                                <svg class="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                                <span class="text-[9px] font-black text-blue-500 uppercase tracking-[0.2em]">Tool Result${c.is_error ? ' (Error)' : ''}</span>
                                ${c.tool_use_id ? `<span class="text-[9px] text-neutral-500">ID: ${c.tool_use_id.slice(0, 8)}...</span>` : ''}
                            </div>
                            ${resultContent ? `<div class="p-3 text-xs text-claude-text-muted whitespace-pre-wrap font-mono">${escapeHtml(resultContent)}</div>` : ''}
                        </div>`;
                }
                contentHtml += '</div>';
            });
            contentHtml += '</div>';
        } else {
            contentHtml = processText(msg.content || '');
        }

        div.innerHTML = `
            <div class="flex items-center justify-between mb-4 border-b border-claude pb-2">
                <span class="text-[9px] font-black uppercase tracking-[0.2em] ${isUser ? 'text-blue-500' : 'text-amber-500'}">${msg.role}</span>
            </div>
            <div class="text-sm markdown-body">${contentHtml}</div>`;
        container.appendChild(div);
    });
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderFinalResponse(item) {
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
        div.className = 'p-8 rounded-lg message-assistant markdown-body border border-amber-900/30 shadow-2xl';
        div.innerHTML = marked.parse(responseText || '*Empty output*');
        responseContainer.appendChild(div);
    } else {
        responseContainer.innerHTML = '<p class="text-neutral-600 italic text-sm font-mono">// no response captured</p>';
    }
}

function renderToolDefinitions(item) {
    const toolsSection = document.getElementById('tools-section');
    const toolsContainer = document.getElementById('tools-container');
    
    if (item.full_request.tools && item.full_request.tools.length > 0) {
        toolsSection.classList.remove('hidden');
        toolsContainer.innerHTML = '';
        item.full_request.tools.forEach((tool, tIdx) => {
            const toolCardId = `tool-${tIdx}`;
            const div = document.createElement('div');
            div.id = toolCardId;
            div.className = 'tool-card rounded-lg overflow-hidden mb-6 shadow-lg';
            
            let propertiesHtml = '';
            if (tool.input_schema?.properties) {
                const req = tool.input_schema.required || [];
                propertiesHtml = '<div class="tool-schema p-5"><p class="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-4">Schema Definition</p><div class="space-y-4">';
                for (const [name, prop] of Object.entries(tool.input_schema.properties)) {
                    propertiesHtml += `
                        <div class="flex flex-col sm:flex-row gap-6 border-b border-claude pb-4 last:border-0 last:pb-0">
                            <div class="min-w-[160px] flex items-center gap-2">
                                <code class="text-amber-500 font-bold text-xs font-mono">${name}</code>
                                ${req.includes(name) ? '<span class="text-[7px] font-black bg-amber-900/40 text-amber-500 px-1.5 py-0.5 rounded uppercase tracking-tighter">Required</span>' : ''}
                            </div>
                            <div class="flex-1">
                                <span class="text-[9px] bg-claude-border text-neutral-400 px-2 py-0.5 rounded font-mono">${prop.type || 'any'}</span>
                                <p class="text-xs text-neutral-500 mt-2 leading-relaxed">${prop.description || ''}</p>
                            </div>
                        </div>`;
                }
                propertiesHtml += '</div></div>';
            }
            
            div.innerHTML = `
                <div class="tool-header p-5 cursor-pointer flex items-center justify-between transition-colors" onclick="toggleTool('${toolCardId}')">
                    <div class="flex items-center gap-4">
                        <div class="p-2 bg-amber-600/10 text-amber-600 rounded border border-amber-600/20"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" stroke-width="2"></path></svg></div>
                        <h4 class="text-sm font-black font-mono tracking-tight">${tool.name}</h4>
                    </div>
                    <svg id="icon-${toolCardId}" class="w-4 h-4 text-neutral-500 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" stroke-width="2"></path></svg>
                </div>
                <div id="content-${toolCardId}" class="hidden border-t border-claude">
                    <div class="p-6 text-[13px] markdown-body leading-relaxed">${marked.parse(tool.description || '')}</div>
                    ${propertiesHtml}
                </div>`;
            toolsContainer.appendChild(div);
        });
    } else {
        toolsSection.classList.add('hidden');
    }
}

function renderTabs(item) {
    document.getElementById('raw-json-code').textContent = JSON.stringify(item, null, 2);
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

function switchTab(view) {
    currentTab = view;
    const renderLayout = document.getElementById('render-layout');
    const raw = document.getElementById('view-raw');
    const rBtn = document.getElementById('tab-render');
    const rwBtn = document.getElementById('tab-raw');
    
    if (view === 'render') {
        renderLayout.classList.remove('hidden');
        raw.classList.add('hidden');
        // Force TOC update if layout is shown
        setTimeout(updateTOC, 0);
        rBtn.classList.add('active');
        rwBtn.classList.remove('active');
    } else {
        renderLayout.classList.add('hidden');
        raw.classList.remove('hidden');
        rBtn.classList.remove('active');
        rwBtn.classList.add('active');
    }
}

function updateTOC() {
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
    addTocItem('section-messages', 'Interaction Log');

    const item = appData.prompts[currentDetailIndex];
    item.full_request.messages.forEach((msg, mIdx) => {
        // Extract preview text from message content
        let previewText = msg.role.toUpperCase();
        let foundContent = false;

        if (msg.content) {
            if (typeof msg.content === 'string') {
                previewText = msg.content.substring(0, 20).replace(/\n/g, ' ').trim();
                foundContent = true;
            } else if (Array.isArray(msg.content)) {
                // Check if this is a tool_result only message (skip it)
                const hasText = msg.content.some(c => c.type === 'text');
                const hasToolUse = msg.content.some(c => c.type === 'tool_use');
                const onlyToolResult = !hasText && !hasToolUse && msg.content.some(c => c.type === 'tool_result');
                if (onlyToolResult) return;  // Skip tool_result only messages

                // Try to find text content (skip text starting with <system-reminder>)
                const textObjs = msg.content.filter(c => c.type === 'text' && c.text && !c.text.startsWith('<system-reminder>'));
                const textObj = textObjs.length > 0 ? textObjs[0] : null;
                if (textObj && textObj.text) {
                    previewText = textObj.text.substring(0, 20).replace(/\n/g, ' ').trim();
                    foundContent = true;
                } else {
                    // Try to find thinking content
                    const thinkingObj = msg.content.find(c => c.type === 'thinking');
                    if (thinkingObj && thinkingObj.thinking) {
                        previewText = thinkingObj.thinking.substring(0, 20).replace(/\n/g, ' ').trim();
                        foundContent = true;
                    } else {
                        // Try to find tool_use name
                        const toolUse = msg.content.find(c => c.type === 'tool_use');
                        if (toolUse && toolUse.name) {
                            previewText = `[${toolUse.name}]`;
                            foundContent = true;
                        }
                    }
                }
            }
        }

        // Only use role if we didn't find actual content
        if (!foundContent) {
            previewText = msg.role.toUpperCase();
        }

        addTocItem(`msg-${mIdx}`, previewText, 1);
    });
    
    addTocItem('section-response', 'Final Response');
    
    if (item.full_request.tools && item.full_request.tools.length > 0) {
        addTocItem('tools-section', 'Tool Definitions');
        item.full_request.tools.forEach((tool, tIdx) => {
            addTocItem(`tool-${tIdx}`, tool.name, 1);
        });
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    fetchData();
    setInterval(checkUpdate, 2000);
});
