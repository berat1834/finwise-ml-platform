import os

filepath = "templates/index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Dark Mode CSS
dark_css = """
        html.dark {
            filter: invert(1) hue-rotate(180deg);
        }
        html.dark img, html.dark canvas, html.dark .fa-solid, html.dark .text-brand-600 {
            filter: invert(1) hue-rotate(180deg);
        }
"""
content = content.replace("</style>", dark_css + "\n    </style>")

# 2. Add Dark Mode Toggle and floating Chatbot to appData state
state_search = """                activeTab: 'app',"""
state_replace = """                isDark: false,
                chatOpen: false,
                activeTab: 'app',"""
content = content.replace(state_search, state_replace)

# 3. Add Dark mode toggle method and watch
init_search = """                init() {"""
init_replace = """                init() {
                    this.$watch('isDark', val => {
                        if (val) document.documentElement.classList.add('dark');
                        else document.documentElement.classList.remove('dark');
                    });
                    // Initialize dark mode from localStorage if needed
                    if(localStorage.getItem('theme') === 'dark') {
                        this.isDark = true;
                    }"""
content = content.replace(init_search, init_replace)

# 4. Add Dark mode toggle button to Navbar
nav_search = """                <button @click="lang = lang === 'tr' ? 'en' : 'tr'\""""
nav_replace = """                <button @click="isDark = !isDark; localStorage.setItem('theme', isDark ? 'dark' : 'light')" class="text-sm font-semibold text-gray-500 hover:text-brand-600 transition" title="Dark Mode Toggle">
                    <i class="fa-solid" :class="isDark ? 'fa-sun' : 'fa-moon'"></i>
                </button>
                <button @click="lang = lang === 'tr' ? 'en' : 'tr'\""""
content = content.replace(nav_search, nav_replace)

# 5. Floating Chatbot UI
chatbot_ui = """
    <!-- Floating Chatbot -->
    <div class="fixed bottom-6 right-6 z-50 flex flex-col items-end">
        
        <!-- Chat Window -->
        <div x-show="chatOpen" x-transition class="bg-white rounded-xl shadow-2xl w-80 mb-4 overflow-hidden border border-gray-200 flex flex-col" style="height: 400px; display: none;">
            <div class="bg-brand-600 text-white p-3 flex justify-between items-center">
                <h3 class="font-bold text-sm"><i class="fa-solid fa-robot mr-2"></i> FinWise Asistan</h3>
                <button @click="chatOpen = false" class="text-white hover:text-gray-200"><i class="fa-solid fa-times"></i></button>
            </div>
            
            <div class="flex-1 p-3 overflow-y-auto bg-gray-50 text-sm" id="floating-chat-history">
                <div class="bg-brand-100 text-brand-800 p-2 rounded-lg mb-2 inline-block">
                    Merhaba! Size nasıl yardımcı olabilirim?
                </div>
                <template x-for="msg in chatMessages" :key="Math.random()">
                    <div :class="msg.role === 'user' ? 'text-right' : 'text-left'" class="mb-2 w-full">
                        <div :class="msg.role === 'user' ? 'bg-gray-200 text-gray-800' : 'bg-brand-100 text-brand-800'" class="p-2 rounded-lg inline-block max-w-[85%] break-words" x-text="msg.text"></div>
                    </div>
                </template>
                <div x-show="loading" class="text-gray-500 text-xs italic mt-1">Yazıyor...</div>
            </div>
            
            <div class="p-2 bg-white border-t border-gray-200">
                <form @submit.prevent="askAssistant" class="flex gap-2">
                    <input type="text" x-model="chatInput" class="flex-1 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:border-brand-500" placeholder="Sorunuzu yazın...">
                    <button type="submit" class="bg-brand-600 hover:bg-brand-700 text-white px-3 py-1 rounded text-sm"><i class="fa-solid fa-paper-plane"></i></button>
                </form>
            </div>
        </div>

        <!-- Floating Button -->
        <button @click="chatOpen = !chatOpen" class="bg-brand-600 hover:bg-brand-700 text-white w-14 h-14 rounded-full shadow-xl flex items-center justify-center text-2xl transform transition hover:scale-110">
            <i class="fa-solid" :class="chatOpen ? 'fa-times' : 'fa-comment-dots'"></i>
        </button>
    </div>
"""

# Insert chatbot UI right before closing body tag or scripts
body_end_search = """    <script>"""
content = content.replace(body_end_search, chatbot_ui + "\n    <script>")

# 6. Add askAssistant JS logic
ask_assistant_js = """
                async askAssistant() {
                    if (!this.chatInput.trim()) return;
                    
                    const question = this.chatInput;
                    this.chatMessages.push({ role: 'user', text: question });
                    this.chatInput = '';
                    this.loading = true;
                    
                    this.$nextTick(() => {
                        const chatContainer = document.getElementById('floating-chat-history');
                        if(chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
                    });
                    
                    try {
                        const res = await fetch('/api/v2/ai-risk-assistant', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.token}` },
                            body: JSON.stringify({
                                question: question,
                                context: this.result ? this.result : this.form
                            })
                        });
                        
                        if (res.ok) {
                            const data = await res.json();
                            this.chatMessages.push({ role: 'assistant', text: data.answer || "Cevap alınamadı." });
                        } else {
                            this.chatMessages.push({ role: 'assistant', text: "Sunucu bağlantı hatası." });
                        }
                    } catch (e) {
                        this.chatMessages.push({ role: 'assistant', text: "Bağlantı hatası." });
                    } finally {
                        this.loading = false;
                        this.$nextTick(() => {
                            const chatContainer = document.getElementById('floating-chat-history');
                            if(chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
                        });
                    }
                },
"""

js_search = """                async fetchFindeks(tckn) {"""
content = content.replace(js_search, ask_assistant_js + "\n                async fetchFindeks(tckn) {")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Added dark mode and floating chatbot to templates/index.html")
