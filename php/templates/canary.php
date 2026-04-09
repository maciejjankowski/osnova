<?php
/**
 * Canary Composer - Whistleblower dead man's switch
 * Capability-gated feature
 */
?>
<link rel="stylesheet" href="/static/css/osnova.css">
<script src="/static/js/stego.js"></script>

<div class="container">
    <h1>🕊️ Canary System</h1>
    <p class="text-muted mb-3">Dead man's switch for whistleblowers</p>
    
    <div id="canary-locked" class="card text-center" style="display:none;">
        <h3>🔒 Locked Feature</h3>
        <p class="text-muted">
            This feature requires advanced ring membership.
            <br>Follow the right people to unlock.
        </p>
    </div>
    
    <div id="canary-composer" style="display:none;">
        <div class="card">
            <h2>Create Canary</h2>
            <p class="text-muted">
                Your message will be fragmented and distributed across your rings.
                If you miss heartbeats, it will be automatically released.
            </p>
            
            <form id="canary-form">
                <div class="form-group">
                    <label>Message *</label>
                    <textarea id="message" rows="10" 
                              placeholder="Your whistleblower disclosure..." 
                              required></textarea>
                    <small class="text-muted">
                        This will be encrypted and fragmented into 100+ pieces
                    </small>
                </div>
                
                <div class="form-group">
                    <label>Heartbeat Interval</label>
                    <select id="heartbeat-interval">
                        <option value="43200">12 hours</option>
                        <option value="86400" selected>24 hours</option>
                        <option value="172800">48 hours</option>
                        <option value="259200">72 hours</option>
                    </select>
                    <small class="text-muted">
                        How often you must check in to prevent release
                    </small>
                </div>
                
                <div class="form-group">
                    <label>Alternative Message (optional)</label>
                    <textarea id="alt-message" rows="3"
                              placeholder="Message to show if you're compromised..."></textarea>
                    <small class="text-muted">
                        Send this if you signal "compromised" - provides cover
                    </small>
                </div>
                
                <button type="submit" class="btn btn-primary">Create Canary</button>
            </form>
        </div>
        
        <div id="active-canaries" class="mt-3">
            <h2>Your Active Canaries</h2>
            <div id="canary-list"></div>
        </div>
    </div>
</div>

<script>
// Check capability
if (osnovaStego.capabilities.has('canary_composer')) {
    document.getElementById('canary-composer').style.display = 'block';
    loadActiveCanaries();
} else {
    document.getElementById('canary-locked').style.display = 'block';
}

// Create canary
document.getElementById('canary-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        message: document.getElementById('message').value,
        heartbeat_interval: parseInt(document.getElementById('heartbeat-interval').value),
        alternative_message: document.getElementById('alt-message').value
    };
    
    const response = await fetch('/api/canary/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    
    if (response.ok) {
        const result = await response.json();
        alert(`Canary created! ID: ${result.canary_id}\n` +
              `Fragments: ${result.fragments}\n` +
              `Next heartbeat: ${new Date(result.next_heartbeat * 1000).toLocaleString()}`);
        
        document.getElementById('canary-form').reset();
        loadActiveCanaries();
    } else {
        alert('Failed to create canary');
    }
});

// Load active canaries
async function loadActiveCanaries() {
    const response = await fetch('/api/canary/list');
    if (response.ok) {
        const data = await response.json();
        renderCanaries(data.canaries || []);
    }
}

function renderCanaries(canaries) {
    const container = document.getElementById('canary-list');
    
    if (canaries.length === 0) {
        container.innerHTML = '<div class="card text-center"><p class="text-muted">No active canaries</p></div>';
        return;
    }
    
    container.innerHTML = canaries.map(c => {
        const nextHeartbeat = new Date((parseFloat(c.last_heartbeat) + parseInt(c.heartbeat_interval)) * 1000);
        const missed = c.missed_count || 0;
        const status = c.status === 'active' ? '✅' : c.status === 'triggered' ? '🔴' : '⚠️';
        
        return `
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h3>${status} Canary ${c.canary_id.substring(0, 8)}</h3>
                        <p class="text-muted">
                            Status: ${c.status}<br>
                            Missed heartbeats: ${missed}/3<br>
                            Next heartbeat: ${nextHeartbeat.toLocaleString()}<br>
                            Fragments: ${c.fragment_count}
                        </p>
                    </div>
                    <div>
                        <button class="btn btn-primary" onclick="sendHeartbeat('${c.canary_id}')">
                            ❤️ Heartbeat
                        </button>
                        ${c.status === 'active' ? `
                            <button class="btn" style="background: #C62828; color: white;" 
                                    onclick="signalCompromised('${c.canary_id}')">
                                ⚠️ Compromised
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function sendHeartbeat(canary_id) {
    const response = await fetch('/api/canary/heartbeat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({canary_id, method: 'manual'})
    });
    
    if (response.ok) {
        alert('Heartbeat recorded ✅');
        loadActiveCanaries();
    } else {
        alert('Failed to record heartbeat');
    }
}

async function signalCompromised(canary_id) {
    if (!confirm('Are you sure you want to signal COMPROMISED?\nThis will trigger immediate cascade release.')) {
        return;
    }
    
    const signal = prompt('Enter compromised signal (or leave empty for default):') || 'COMPROMISED';
    
    const response = await fetch('/api/canary/compromised', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({canary_id, signal})
    });
    
    if (response.ok) {
        alert('Compromised signal sent. Cascade triggered.');
        loadActiveCanaries();
    }
}
</script>
