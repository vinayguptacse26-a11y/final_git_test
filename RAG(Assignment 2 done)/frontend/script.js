const API_BASE = ""; // Relative to current host

// 1. TABS: SWITCHING LOGIC
function switchTab(evt, tabId) {
    // Fallback: If evt is a string, it means the event object was omitted in HTML
    if (typeof evt === 'string') {
        tabId = evt;
        evt = null;
    }

    // Robust selector: Handles both 'tab-content' and 'tab-view' classes
    const allTabs = document.querySelectorAll('.tab-content, .tab-view');
    allTabs.forEach(el => el.classList.remove('active'));

    // Handle different button classes (nav-item vs tab-btn)
    const allBtns = document.querySelectorAll('.nav-item, .tab-btn');
    allBtns.forEach(el => el.classList.remove('active'));
    
    // Activate specific tab
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.classList.add('active');
    } else {
        console.error(`Tab with ID '${tabId}' not found in HTML.`);
    }

    // Activate the clicked button
    if (evt && evt.currentTarget) {
        evt.currentTarget.classList.add('active');
    }
}

// 2. DYNAMIC INGESTION LOGIC
function toggleIndexUI() {
    const mode = document.querySelector('input[name="index-mode"]:checked').value;
    const selectWrap = document.getElementById("existing-index-wrapper");
    const inputWrap = document.getElementById("new-index-wrapper");
    const newInput = document.getElementById("index-input");

    if (mode === "new") {
        selectWrap.style.display = "none";
        inputWrap.style.display = "block";
        if(newInput) newInput.focus();
    } else {
        selectWrap.style.display = "block";
        inputWrap.style.display = "none";
    }
}

function handleFileSelect() {
    const file = document.getElementById("upload-file").files[0];
    if (!file) return;
    
    document.getElementById("file-label").innerText = `Selected: ${file.name}`;
    
    // Auto-select strategies based on file type
    const ext = file.name.split('.').pop().toLowerCase();
    const strategySelect = document.getElementById("chunk-strategy");
    let options = [];

    if (ext === "pptx") {
        options = ["Slide Aware", "Image Aware"];
    } else {
        options = ["Fixed", "Paragraph", "Section Aware", "Token Based"];
    }
    
    strategySelect.innerHTML = options.map(opt => `<option value="${opt}">${opt}</option>`).join('');
    updateParamLabels();
}

function updateParamLabels() {
    const strategy = document.getElementById("chunk-strategy").value;
    const label = document.getElementById("param-label");
    const input = document.getElementById("param-value");

    if (strategy === "Token Based") {
        label.innerText = "Max Tokens";
        input.value = 512;
    } else if (strategy === "Fixed") {
        label.innerText = "Max Characters";
        input.value = 500;
    } else {
        label.innerText = "Limit (Default)";
        input.value = 500;
    }
}

async function loadIndices() {
    try {
        const res = await fetch(`${API_BASE}/indices`);
        const list = await res.json();
        const opts = list.map(i => `<option value="${i}">${i}</option>`).join('');
        
        // Populate both the Ingestion select and the Search select
        document.getElementById("index-select").innerHTML = opts;
        document.getElementById("search-index").innerHTML = opts;
    } catch (e) { console.error("Error loading indices:", e); }
}

async function startIngestion() {
    const file = document.getElementById("upload-file").files[0];
    const mode = document.querySelector('input[name="index-mode"]:checked').value;
    const status = document.getElementById("ingest-status");

    let indexName = (mode === "new") 
        ? document.getElementById("index-input").value.trim()
        : document.getElementById("index-select").value;

    if (!file || !indexName) return alert("Please select a file and index.");

    const form = new FormData();
    form.append("file", file);
    form.append("index_type", indexName);
    form.append("chunking_strategy", document.getElementById("chunk-strategy").value);
    form.append("max_chars", document.getElementById("param-value").value); 

    status.innerHTML = `<span style="color:var(--primary)">⏳ Processing...</span>`;

    try {
        const res = await fetch(`${API_BASE}/ingest`, { method: "POST", body: form });
        if (res.ok) {
            status.innerHTML = `<span style="color:green">✅ Success! Index Updated.</span>`;
            loadIndices(); // Refresh list to include new index
        } else {
            const err = await res.json();
            status.innerHTML = `<span style="color:red">❌ Error: ${err.detail}</span>`;
        }
    } catch (e) { status.innerText = "❌ Network Error"; }
}

// 3. CHAT LOGIC

function appendMsg(role, text) {
    const chat = document.getElementById("chat-window");
    const div = document.createElement("div");
    div.className = role === 'user' ? "msg-user" : "msg-ai";
    
    if (role === 'ai') {
        // AI messages have dedicated slots for Metadata, Text, and Citations
        div.innerHTML = `
            <div class="meta-area"></div>
            <div class="text-content">${text}</div>
            <div class="citation-box"></div>
        `;
    } else {
        // User messages can contain HTML (e.g., image previews)
        div.innerHTML = text; 
    }
    
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
}

function showImagePreview() {
    const file = document.getElementById("chat-image").files[0];
    if (file) document.getElementById("image-preview-area").innerText = `📷 Attached: ${file.name}`;
}

// --- TEXT TO SPEECH (OUTPUT) ---
function speakText(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0; 
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    }
}

async function sendQuery() {
    const qInput = document.getElementById("query-text");
    const q = qInput.value.trim();
    if (!q) return;

    // 1. Handle User Message & Image Preview in Chat
    const imgFile = document.getElementById("chat-image").files[0];
    let userDisplay = q;
    
    if (imgFile) {
        // If image exists, show a mini preview in user bubble
        userDisplay = `<div>${q}</div><div style="font-size:0.8rem; color:#e0e7ff; margin-top:5px;"><i class="fas fa-image"></i> ${imgFile.name}</div>`;
    }
    
    appendMsg("user", userDisplay);
    qInput.value = "";
    document.getElementById("image-preview-area").innerText = ""; // Clear helper text
    
    // 2. Prepare AI Bubble
    const aiDiv = appendMsg("ai", "...");
    const textEl = aiDiv.querySelector(".text-content");
    const metaEl = aiDiv.querySelector(".meta-area");
    const citeEl = aiDiv.querySelector(".citation-box");
    textEl.innerText = ""; // Clear the dots

    // Stop previous speech
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();

    try {
        let response;
        if (imgFile) {
            // --- Visual Query ---
            const fd = new FormData();
            fd.append("question", q);
            fd.append("image", imgFile);
            fd.append("index_type", document.getElementById("search-index").value);
            response = await fetch(`${API_BASE}/query-visual`, { method: "POST", body: fd });
            document.getElementById("chat-image").value = ""; // Reset file input
        } else {
            // --- Text Stream ---
            response = await fetch(`${API_BASE}/query-stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: q,
                    index_type: document.getElementById("search-index").value,
                    search_type: document.getElementById("search-type").value,
                    top_k: parseInt(document.getElementById("top-k").value)
                })
            });
        }

        // 3. Process Stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullTextForSpeech = ""; 

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            lines.forEach(line => {
                // A. Metadata Line (Citations & Cache)
                if (line.startsWith('metadata:')) {
                    try {
                        const meta = JSON.parse(line.replace('metadata:', '').trim());
                        
                        // Cache Badge
                        if (meta.cache) {
                            metaEl.innerHTML = `<span class="cache-badge">⚡ Cached</span>`;
                        }
                        
                        // Citation Chips
                        if (meta.citations && meta.citations.length > 0) {
                            citeEl.innerHTML = meta.citations.map(c => 
                                // Use c.display (generated by backend) OR fallback to source
                                `<span class="citation-pill">
                                    <i class="fas fa-file-alt"></i> ${c.display || c.source || "Document"}
                                </span>`
                            ).join('');
                        }
                    } catch (e) { console.error("Meta parse error", e); }
                } 
                // B. Data Line (Text Token)
                else if (line.startsWith('data: ')) {
                    const txt = line.replace('data: ', '');
                    buffer += txt;
                    fullTextForSpeech += txt; 
                    textEl.innerText = buffer; // Updates UI word-by-word
                }
            });
            document.getElementById("chat-window").scrollTop = document.getElementById("chat-window").scrollHeight;
        }

        // 4. Speak Result
        speakText(fullTextForSpeech);

    } catch (e) { 
        textEl.innerText = "Error connecting to server."; 
        console.error(e);
    }
}

// 4. SPEECH TO TEXT (INPUT) - BROWSER NATIVE
document.addEventListener("DOMContentLoaded", () => {
    const micBtn = document.getElementById("mic-btn");
    const queryInputEle = document.getElementById("query-text");

    // Support Chrome, Edge, Safari
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = false; 
        recognition.lang = "en-US"; 
        recognition.interimResults = false;

        if (micBtn && queryInputEle) {
            micBtn.onmousedown = () => {
                try {
                    recognition.start();
                    micBtn.style.color = "#ef4444"; // Visual feedback
                    queryInputEle.placeholder = "Listening...";
                } catch (e) { console.error(e); }
            };

            micBtn.onmouseup = () => {
                recognition.stop();
                micBtn.style.color = "";
                queryInputEle.placeholder = "Ask a question...";
            };
        }

        recognition.onresult = (event) => {
            if (queryInputEle) {
                const transcript = event.results[0][0].transcript;
                queryInputEle.value = transcript;
                sendQuery(); // Auto-send when speaking stops
            }
        };

        recognition.onerror = (e) => {
            console.error("Speech error", e);
            if (micBtn) micBtn.style.color = "";
            if (queryInputEle) queryInputEle.placeholder = "Error. Try typing.";
        };
    } else {
        // Hide mic if browser doesn't support API
        if (micBtn) micBtn.style.display = "none";
    }

    // Initialize indices when DOM is fully ready
    loadIndices();
});