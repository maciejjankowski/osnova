<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Osnova</title>
    <link rel="stylesheet" href="/static/css/osnova.css">
</head>
<body>
    <div class="onboard-container">
        <div class="step-indicator">
            <div class="step-dot active"></div>
            <div class="step-dot"></div>
            <div class="step-dot"></div>
            <div class="step-dot"></div>
        </div>
        
        <div id="step-1" class="onboard-step">
            <h1>Welcome to Osnova</h1>
            <p class="text-muted mb-3">The social network that pays you back.</p>
            
            <div class="card text-left mb-3">
                <h3>👥 Connect with friends</h3>
                <p class="text-muted">Encrypted by default. Your data, your control.</p>
            </div>
            
            <div class="card text-left mb-3">
                <h3>💼 Find gigs</h3>
                <p class="text-muted">Earn money helping your network.</p>
            </div>
            
            <div class="card text-left mb-3">
                <h3>🔒 Keep it private</h3>
                <p class="text-muted">Ring-based trust. No corporate tracking.</p>
            </div>
            
            <button class="btn btn-primary mt-3" onclick="nextStep(2)">Get Started</button>
        </div>
        
        <div id="step-2" class="onboard-step" style="display:none;">
            <h2>Create Your Identity</h2>
            <p class="text-muted mb-3">No email required. We don't track you.</p>
            
            <form id="identity-form" class="text-left">
                <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" id="display-name" placeholder="How should others see you?" required>
                </div>
                
                <div class="form-group">
                    <label>Bio (optional)</label>
                    <textarea id="bio" placeholder="Tell us about yourself..."></textarea>
                </div>
                
                <p class="text-muted" style="font-size: 0.875rem;">
                    💡 Your identity is cryptographic. Your keys stay in your browser. 
                    No passwords, no accounts.
                </p>
                
                <button type="submit" class="btn btn-primary mt-3">Continue</button>
            </form>
        </div>
        
        <div id="step-3" class="onboard-step" style="display:none;">
            <h2>Find Your Friends</h2>
            <p class="text-muted mb-3">Were you invited? Enter the code below.</p>
            
            <form id="invite-form" class="text-left">
                <div class="form-group">
                    <label>Invite Code (optional)</label>
                    <input type="text" id="invite-code" placeholder="Ask your friend for their code">
                </div>
                
                <p class="text-muted" style="font-size: 0.875rem;">
                    💡 Invite codes link you to trust rings. You can skip this and explore publicly first.
                </p>
                
                <button type="submit" class="btn btn-primary mt-3">Continue</button>
                <button type="button" class="btn btn-secondary mt-3" onclick="nextStep(4)">Skip for now</button>
            </form>
        </div>
        
        <div id="step-4" class="onboard-step" style="display:none;">
            <h2>Quick Tour</h2>
            
            <div class="card text-left mb-3">
                <h3>👥 Your Ring</h3>
                <p class="text-muted">People you trust. Encrypted by default.</p>
            </div>
            
            <div class="card text-left mb-3">
                <h3>💼 Gigs</h3>
                <p class="text-muted">Earn money helping your network. Post requests, complete tasks.</p>
            </div>
            
            <div class="card text-left mb-3">
                <h3>📬 Messages</h3>
                <p class="text-muted">Private, secure, yours. No peeking.</p>
            </div>
            
            <a href="/feed" class="btn btn-primary mt-3">Start Exploring</a>
        </div>
    </div>
    
    <script>
        let currentStep = 1;
        
        function nextStep(step) {
            document.getElementById(`step-${currentStep}`).style.display = 'none';
            document.getElementById(`step-${step}`).style.display = 'block';
            
            const dots = document.querySelectorAll('.step-dot');
            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i < step);
            });
            
            currentStep = step;
        }
        
        document.getElementById('identity-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const displayName = document.getElementById('display-name').value;
            const bio = document.getElementById('bio').value;
            
            // Generate keypair and store locally
            const response = await fetch('/api/identity', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({display_name: displayName, bio})
            });
            
            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('osnova_identity', JSON.stringify(data));
                nextStep(3);
            }
        });
        
        document.getElementById('invite-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const inviteCode = document.getElementById('invite-code').value;
            
            if (inviteCode) {
                // Process invite code
                const response = await fetch('/api/rings/join', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({invite_code: inviteCode})
                });
                
                if (response.ok) {
                    nextStep(4);
                }
            } else {
                nextStep(4);
            }
        });
    </script>
</body>
</html>
