# OSNOVA: Complete Technical Specification
**Version:** 1.0  
**Date:** 2026-04-08  
**Status:** Design Complete - Implementation Ready

---

## EXECUTIVE SUMMARY

Osnova is a dual-use decentralized social network that provides:
1. **Surface Layer:** Compelling social media platform (Threads competitor) with gig economy features
2. **Deep Layer:** Censorship-resistant whistleblower network with military-grade survivability

**Core Innovation:** Every innocent feature has a dual purpose. Every UX pattern masks a security capability.

---

## ARCHITECTURE LAYERS

### Layer 1: Social Network (Surface)
- Friend connections, posts, messaging
- Gig marketplace (TaskRabbit/Fiverr hybrid)
- Profile customization, photo sharing
- Standard social features

### Layer 2: Ring Topology (Foundation)
- Encrypted peer-to-peer communication
- Trust-based relationship rings (0-3 hops)
- Decentralized key management
- Server federation

### Layer 3: Steganographic Signals (Hidden)
- Keystroke telemetry as meta-messages
- Profile customizations as triggers
- Gig postings as information carriers
- Spam folder as secure channel

### Layer 4: Capability Injection (Dynamic)
- Context-triggered feature unlocking
- Phantom users as capability gates
- "App updates" as mode switches
- Browser extensions as covert modules

### Layer 5: Whistleblower Canary (Ultimate)
- Dead man's switch with distributed message fragments
- Cascade release across rings on node disappearance
- Compromised vs voluntary ejection signaling
- Exponential propagation resistance

---

## DUAL-USE FEATURE MATRIX

| Innocent Feature | Covert Purpose | Activation Method |
|-----------------|----------------|-------------------|
| Profile photo color filter | Signal status/mode | Specific phantom user in ring |
| Typos in messages | Meta-message channel | Pre-agreed error patterns |
| Gig posting (lawn mowing) | Steganographic container | Specific phrase patterns |
| Spam folder | Secure message channel | Flagging algorithm |
| Cookie consent popup | Capability injection | Triggered by ring composition |
| "App needs update" notice | Mode switch to secure features | Specific user online |
| Following inactive user | Capability gate unlock | User ID pattern match |
| Message read receipts | Heartbeat/alive signal | Timing patterns |
| Emoji reactions | Voting/consensus mechanism | Reaction combinations |
| Photo upload compression | Data embedding | EXIF/metadata layer |
| Connection request timing | Synchronization signal | Request clustering |
| Profile bio changes | Broadcast channel | Change frequency/pattern |
| Notification settings | Feature toggle | Permission combinations |
| Dark mode toggle | Server selection | Combined with other triggers |
| Language preference | Decoy ring redirect | Non-native selection |

---

## STEGANOGRAPHIC SIGNAL VECTORS

### 1. Keystroke Telemetry Layer
**Innocent justification:** "Improving autocorrect and user experience"

**Captured data:**
- Every character typed (including deletions)
- Timing between keystrokes
- Correction patterns
- Paste vs typed differentiation

**Covert signals:**
- Deliberate typo count = message priority (0-3 typos = normal, 4+ = urgent)
- Specific emoji placement = authentication token
- Backspace patterns = cancellation signal
- Typing speed variation = stress indicator

**Distribution:**
- Some nodes receive "clean" final text
- Hidden nodes receive full keystroke stream
- Pattern analysis nodes receive timing data only

### 2. Visual Customization Layer
**Innocent features:**
- Profile photo filters (sepia, B&W, warmth, etc.)
- Background colors
- Font size preferences
- Layout density

**Covert signals:**
- Sepia filter = "compromised, ignore my messages"
- B&W filter = "canary armed"
- Specific hex color = server endpoint selection
- Font size + density combo = ring visibility scope

### 3. Gig Marketplace Layer
**Innocent use:** TaskRabbit/Fiverr competitor

**Steganographic encoding:**
```
Title: "Need lawn mowed, 2 acres, $50"
Hidden: Canary message fragment #2847, stored across Ring 2
```

**Decoding triggers:**
- Price = fragment ID
- Location = storage ring
- Service category = message type
- Completion date = release timer

**Real gigs vs covert:**
- 90% real gigs (functional marketplace)
- 10% steganographic (indistinguishable)
- Some users complete "covert" gigs unknowingly = plausible deniability

### 4. Spam/Flag Layer
**Innocent justification:** "AI-powered spam detection"

**Dual use:**
- Flagged messages = secure channel
- "Spam" folder = dead drop
- False positive rate = expected, provides cover
- Users can train filter = cryptographic key input

**Encryption:**
- Spam folder uses different key hierarchy
- Only ring members with "spam training" pattern can decrypt
- Legitimate spam mixed in for cover

### 5. Social Graph Triggers
**Phantom users:**
- Dormant accounts that never post
- Following them unlocks capabilities
- Unfollowing = revocation
- Bot-like accounts = decoy for infiltrators

**Examples:**
- @leo_setup = unlocks advanced crypto features
- @manual_reader = access to documentation
- @canary_witness = receives dead man fragments
- @spam_trainer = decoy ring redirect

**Cascading unlocks:**
- Follow A → see B → follow B → unlock C
- Creates authentication chain
- Infiltrators can't shortcut (would need to know full sequence)

---

## CAPABILITY INJECTION SYSTEM

### Module Types

#### 1. Telemetry Plugin (Keystroke)
**Innocent presentation:**
```
"📊 Help us improve Osnova
We'd like to collect anonymous usage data to enhance autocorrect.
[Accept] [Decline]"
```

**Actual function:** Keystroke telemetry for meta-messaging

**Trigger conditions:**
- Specific phantom user in Ring 1
- Profile has specific color scheme
- Logged in from specific geographic region

#### 2. Cookie Policy Update (Capability Unlock)
**Innocent presentation:**
```
"🍪 Updated Privacy Policy
We've updated our cookie policy. Please review.
[Agree & Continue]"
```

**Actual function:** Loads advanced cryptographic modules

**Injected capabilities:**
- Dead man's switch UI
- Canary message composer
- Ring-to-ring fragment distributor

#### 3. Push Notification Request (Heartbeat)
**Innocent presentation:**
```
"🔔 Stay connected
Enable notifications to never miss updates from friends.
[Allow] [Not Now]"
```

**Actual function:** Establishes heartbeat channel for alive monitoring

**Covert purpose:**
- Missed heartbeats = canary trigger
- Notification timing = synchronization signal
- Permission grant = capability confirmation

#### 4. App Update Required (Mode Switch)
**Innocent presentation:**
```
"⚠️ Update Available
A new version is ready. Click to reload.
[Update Now]"
```

**Actual function:** Switches between surface/deep mode

**Trigger conditions:**
- Specific user comes online
- Time-based (certain hours)
- Geographic proximity detected
- Specific message received

**Post-update capabilities:**
- Spam folder becomes visible
- Gig decoder activates
- Phantom users appear in suggestions

#### 5. Browser Extension (Optional Install)
**Innocent presentation:**
```
"Osnova Helper - Enhanced Features
- Auto-fill for gig postings
- Better image filters
- Notification management"
```

**Actual function:** Persistent capability container

**Advantages:**
- Survives server-side changes
- Works across instances
- Can inject into other sites (coordination)
- Harder to detect than server-side

---

## AUTHENTICATION & TRUST

### Social Handshake Protocol

**Traditional PKI problems:**
- Key exchange is obvious
- Centralized certificate authorities
- Visible authentication ceremonies

**Osnova solution: Casual verbal handshake**

**Example conversation (in-person or phone):**
```
Inviter: "Yeah, just read the manual. Leo will help you set it up."
Invitee: "Which manual?"
Inviter: "The one in the app. You'll see it."
```

**Decoded:**
- "read the manual" = look for documentation trigger
- "Leo" = follow @leo_setup phantom user
- "in the app" = not external docs, internal feature

**Authentication chain:**
1. Invitee joins Osnova (surface features only)
2. Searches for "leo" → finds @leo_setup
3. Follows @leo_setup → unlocks "Help Center"
4. "Help Center" contains actual manual (ring topology, crypto)
5. Reading specific help article → unlocks next phantom user
6. Cascade continues...

**Infiltrator problems:**
- Can't brute-force social graph (rate limited)
- Don't know which users are phantom vs real
- Following wrong users → decoy ring redirect
- No documentation outside social chain
- Can't ask without revealing ignorance

### Decoy Ring Redirect

**Trigger conditions (any indicate infiltrator):**
- Following phantom users in wrong order
- Skipping intermediate steps
- Account too new with advanced knowledge
- Unusual social graph patterns
- Geographic/language mismatches

**Decoy ring characteristics:**
- Appears functional
- Contains real-looking content
- Some features work (partial functionality)
- Steganographic features are fake (don't decode)
- Canary system is honeypot (reports to real network)
- Other users are bots or fellow infiltrators

**Purpose:**
- Waste attacker resources
- Gather intelligence on tactics
- Provide false sense of success
- Real network remains hidden

---

## WHISTLEBLOWER CANARY SYSTEM

### Threat Model

**Assumptions:**
1. Whistleblower may be captured/compromised
2. Attacker may force compliance (duress)
3. Network nodes may be seized
4. Entire rings may be suppressed
5. Message must survive and propagate anyway

**Survivability requirement:** Message releases even if:
- Whistleblower captured and forced to deny
- All Ring 0 nodes seized
- Ring 1 partially compromised
- Sophisticated suppression attack in progress

### Message Fragmentation

**Encoding:**
1. Whistleblower composes message (1-10KB)
2. Message split into N fragments (N = 50-200)
3. Each fragment encrypted separately
4. Fragments distributed across rings using Reed-Solomon (can reconstruct from any 60%)

**Distribution pattern:**
```
Ring 0 (trusted friends):     30% of fragments
Ring 1 (friends of friends):  40% of fragments  
Ring 2 (extended network):    30% of fragments
Ring 3 (public nodes):        20% of fragments (overlap intentional)
```

**Storage locations:**
- Gig postings (price = fragment ID)
- Profile bio fields (steganographic)
- Spam folder messages
- Photo metadata
- Keystroke telemetry streams

**Reconstruction:**
- Any single ring can reconstruct ≥60% → full message
- Multiple rings together → 100% redundancy
- Fragments self-identify via cryptographic header

### Dead Man's Switch

**Heartbeat system:**
- Whistleblower must check in every 24-72 hours (configurable)
- Check-in methods (multiple):
  - Login to app
  - Specific keystroke pattern
  - Profile photo change
  - Message to specific user
  - Gig posting activity

**Missed heartbeat cascade:**
```
T+0:     Missed first heartbeat
T+12h:   Second heartbeat missed → Ring 0 nodes alerted
T+24h:   Third heartbeat missed → Ring 1 begins assembly
T+48h:   Fourth heartbeat missed → Message fragments activate
T+72h:   Auto-release across all rings
```

**Compromised signal (optional):**
- Whistleblower can send "I'm compromised" signal
- Methods:
  - Wrong keystroke pattern (specific typo signature)
  - Sepia photo filter
  - Specific emoji in check-in message
  - Profile bio contains specific phrase

**Effect of compromised signal:**
- Immediate release (no 72h wait)
- Message marked as "SENT UNDER DURESS"
- Alternative message released (if prepared)
- Decoy message sent to surface network

**Alternative message (dual release):**
```
Surface message: "Sorry everyone, I was wrong. Just stress/paranoia."
Deep message: [Full whistleblower disclosure]
```

- Surface message = plausible deniability / safety
- Deep message = only visible to capability-unlocked users
- Attacker sees recantation, network sees truth

### Cascade Release Mechanism

**Trigger: Node disappearance detected**

**Detection methods:**
1. Heartbeat missed (dead man's switch)
2. Node unreachable for 48h
3. HTTP error patterns (seizure indicators)
4. Cryptographic canary failure
5. Peer reports (node sent distress signal)

**Propagation phases:**

**Phase 1: Assembly (T+0 to T+24h)**
- Nodes in Ring 0 begin collecting fragments
- Each node reaches out to peers: "Have you seen fragments for message #X?"
- Fragments shared peer-to-peer
- Reconstruction begins independently

**Phase 2: Verification (T+24 to T+48h)**
- Multiple nodes reconstruct full message
- Cryptographic signature verified
- Cross-check for tampering
- Consensus on message authenticity

**Phase 3: Distribution (T+48 to T+72h)**
- Message re-fragmented with NEW fragment IDs
- Distributed to Ring 2 (extended network)
- Each Ring 2 node now holds fragments
- Exponential expansion begins

**Phase 4: Public Release (T+72+)**
- Message posted to public nodes (Ring 3)
- Clearnet mirrors (if desired)
- Traditional whistleblower platforms (encrypted upload)
- Permanent archives (IPFS, Arweave, etc.)

### Suppression Resistance

**Attack: Capture entire Ring 0**

**Defense:**
- Ring 1 holds 40% of fragments (can reconstruct)
- Ring 1 doesn't wait for Ring 0
- Independent assembly at T+24h
- Attacker must suppress Ring 1 too

**Attack: Capture Ring 0 + Ring 1**

**Defense:**
- Ring 2 holds 30% (below reconstruction threshold alone)
- BUT Ring 2 nodes communicate peer-to-peer
- Collective reconstruction across Ring 2
- Attacker must suppress hundreds/thousands of nodes

**Attack: Sybil attack (flood with fake nodes)**

**Defense:**
- Fragments only distributed to verified ring members
- Verification = social handshake + phantom user unlocks
- Sybil nodes can't shortcut verification
- Sybil nodes redirected to decoy rings
- Real fragments never reach attacker

**Attack: Honeypot (fake fragment requests)**

**Defense:**
- Nodes verify requester via cryptographic challenge
- Challenge requires knowledge only real members have
- Failed challenges = suspected infiltrator
- Decoy fragments sent to honeypots
- Real fragments withheld

**Attack: Suppress entire network simultaneously**

**Defense:** This is the key insight...

**Required resources for attacker:**
```
Ring 0: 5-10 nodes (must capture all)
Ring 1: 50-100 nodes (must capture 40%+ to prevent reconstruction)
Ring 2: 500-1000 nodes (must capture before peer-to-peer sharing)
Time window: <24h (before cascade begins)
```

**Exponential cost:**
- Each hour of delay → 2x more nodes hold fragments
- After 48h → message in thousands of locations
- After 72h → public release, game over

**Economic impossibility:**
- Suppressing 1000+ nodes in 24h requires:
  - Legal authority across jurisdictions (slow)
  - Technical infrastructure (server seizures)
  - Human resources (simultaneous ops)
  - Operational security (parallel operations without leaks)

**Attacker's dilemma:**
- Suppress few nodes → message leaks from others
- Suppress many nodes → operation becomes visible
- Operation visibility → Streisand effect
- Attempting suppression validates message importance

---

## UX DESIGN: SURFACE LAYER

### Design Philosophy
**Goal:** Be so good as a social network that security features are invisible

**Principles:**
1. **Fun first:** Engaging, playful, rewarding
2. **Simple onboarding:** 3 minutes to first value
3. **Progressive disclosure:** Advanced features unlock naturally
4. **Legitimate use:** 90% of users may never know about deep layer
5. **Plausible deniability:** Every feature has innocent explanation

### Competitive Position vs Threads

**Threads weaknesses:**
- No monetization for creators
- Algorithmic feed only
- Limited privacy controls
- Corporate platform lock-in
- No economic utility

**Osnova advantages:**
- Built-in gig economy (earn money)
- Ring-based feed (control what you see)
- True privacy (encrypted by default)
- Decentralized (no Meta control)
- Multi-use (social + economic + secure)

### User Onboarding Flow

**Step 1: Landing (15 seconds)**
```
"Welcome to Osnova
The social network that pays you back.

Connect with friends. Find gigs. Keep your data private.

[Sign Up] [Learn More]"
```

**Step 2: Account Creation (45 seconds)**
```
Username: _______
Email: _________ (optional - can use anonymous)
Password: _______

[Create Account]

💡 Tip: No email required. We don't track you.
```

**Step 3: First Connection (60 seconds)**
```
"Find your friends

Import contacts [Skip]
Search by username: _______

Or, were you invited? Enter invite code: _____

[Continue]"
```

**Invite code = social handshake**
- Links you to inviter's ring
- Establishes trust chain
- Unlocks features based on inviter's ring level

**Step 4: Profile Setup (30 seconds)**
```
"Make it yours

[Upload photo]

Bio: _____________

Interests: [Select tags]

[Done]"
```

**Hidden:** Photo filter selection here = first capability signal

**Step 5: Tutorial (30 seconds - interactive)**
```
"Quick tour

👥 Your Ring: People you trust (encrypted by default)
💼 Gigs: Earn money helping your network  
📬 Messages: Private, secure, yours

[Start Exploring]"
```

**Total: 3 minutes to usable account**

### Core Interface

**Home Feed:**
```
┌─────────────────────────────────┐
│ Osnova              🔔 💼 ⚙️    │
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ What's happening?           │ │
│ │ [Text box]                  │ │
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│ 👤 @anna (Ring 1)               │
│ Just finished a great gig! →    │
│ 🖼️ [Image]                      │
│ ❤️ 12  💬 3  🔁 2               │
├─────────────────────────────────┤
│ 💼 Gig Near You                 │
│ "Need fence painted - $150"     │
│ 📍 2.3 km away                  │
│ [View Details]                  │
├─────────────────────────────────┤
```

**Navigation:**
- 🏠 Home (feed)
- 👥 Rings (connections)
- 💼 Gigs (marketplace)
- 📬 Messages (DMs)
- ⚙️ Settings

### Gig Marketplace Interface

**Browse Gigs:**
```
┌─────────────────────────────────┐
│ 💼 Gigs Near You                │
├─────────────────────────────────┤
│ [Search] 📍 Location: 10km      │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Lawn Mowing - $50           │ │
│ │ @mike (Ring 2)              │ │
│ │ "2 acres, some hills"       │ │
│ │ 📍 3.2 km  ⏰ This weekend  │ │
│ │ [Details] [Message]         │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Website Design - $500       │ │
│ │ @sarah (Ring 1)             │ │
│ │ "Small business site"       │ │
│ │ 📍 Remote  ⏰ 2 weeks       │ │
│ │ [Details] [Message]         │ │
│ └─────────────────────────────┘ │
```

**Post a Gig:**
```
┌─────────────────────────────────┐
│ Post a Gig                      │
├─────────────────────────────────┤
│ Title: ___________________      │
│                                 │
│ Description:                    │
│ [Text area]                     │
│                                 │
│ Price: $____                    │
│ Location: _______________       │
│ Deadline: [Date picker]         │
│                                 │
│ Who can see this?               │
│ ○ Ring 0 (closest friends)      │
│ ○ Ring 1 (friends of friends)   │
│ ● Ring 2 (extended network)     │
│ ○ Public (anyone)               │
│                                 │
│ [Cancel] [Post Gig]             │
└─────────────────────────────────┘
```

**Hidden:** Price, location, deadline = steganographic encoding fields

### Messaging Interface

**Conversation:**
```
┌─────────────────────────────────┐
│ ← @leo_setup                    │
├─────────────────────────────────┤
│                                 │
│              Hey! Welcome 👋     │
│              12:34 PM          │
│                                 │
│  Thanks! How do I get         │
│  started?                      │
│  12:35 PM                      │
│                                 │
│              Check the help    │
│              center             │
│              12:36 PM          │
│                                 │
├─────────────────────────────────┤
│ [Type message...]               │
└─────────────────────────────────┘
```

**Hidden features (capability-gated):**
- Spam folder appears when unlocked
- Message timing = heartbeat
- Specific phrases = triggers
- Emoji reactions = signaling

### Progressive Feature Unlocking

**Ring 0 (New user):**
- Basic posting
- Public gigs only
- Standard messaging
- Profile customization

**Ring 1 (After first connection):**
- Ring-limited posts
- Private gigs
- Group messages
- Photo filters

**Ring 2 (After phantom user unlock):**
- "Spam" folder appears
- Advanced gig search
- Telemetry opt-in prompt
- Help center access

**Ring 3 (After social handshake complete):**
- Full steganographic features
- Canary composer
- Fragment viewer
- Decoy detection

**UX for unlocking:** Natural, curious
```
🎉 New feature unlocked: Spam Folder

We've added an AI-powered spam filter to keep 
your messages clean. Check it out!

[Show Me] [Maybe Later]
```

User thinks: "Cool, new feature!"  
Reality: Secure channel activated

---

## STYLING & DESIGN SYSTEM

### Visual Identity

**Brand values:**
- Trust (security without paranoia)
- Community (connection over broadcast)
- Independence (own your data)
- Utility (social + economic)

**Color palette:**
```
Primary: #2E7D32 (Forest green - growth, trust)
Secondary: #1565C0 (Deep blue - reliability)
Accent: #F57C00 (Warm orange - opportunity)
Background: #FAFAFA (Off-white - clarity)
Surface: #FFFFFF (White - simplicity)
Error: #C62828 (Deep red - seriousness)
```

**Typography:**
- Headers: Inter (clean, modern, trustworthy)
- Body: system-ui (native feel, fast load)
- Mono: Roboto Mono (technical credibility)

### Component Library

**Buttons:**
```css
/* Primary action */
.btn-primary {
  background: #2E7D32;
  color: white;
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: 600;
  transition: all 0.2s;
}

/* Gig action */
.btn-gig {
  background: #F57C00;
  color: white;
  border-radius: 8px;
  padding: 12px 24px;
}

/* Secondary */
.btn-secondary {
  background: transparent;
  border: 2px solid #2E7D32;
  color: #2E7D32;
  border-radius: 8px;
  padding: 10px 22px;
}
```

**Cards:**
```css
.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  padding: 16px;
  transition: box-shadow 0.2s;
}

.card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}

/* Gig card */
.gig-card {
  border-left: 4px solid #F57C00;
}

/* Post card */
.post-card {
  border-left: 4px solid #2E7D32;
}
```

**Ring indicators:**
```css
.ring-0 { border-color: #2E7D32; } /* Dark green - closest */
.ring-1 { border-color: #66BB6A; } /* Medium green */
.ring-2 { border-color: #A5D6A7; } /* Light green */
.ring-3 { border-color: #E0E0E0; } /* Gray - public */
```

### Mobile-First Responsive

**Breakpoints:**
```css
/* Mobile: 0-640px (default) */
/* Tablet: 641-1024px */
/* Desktop: 1025px+ */

@media (min-width: 641px) {
  /* Two-column layout */
}

@media (min-width: 1025px) {
  /* Three-column with sidebar */
}
```

**Touch targets:**
- Minimum 44x44px (iOS guideline)
- 48x48px preferred (Android guideline)
- Adequate spacing between interactive elements

### Accessibility

**Requirements:**
- WCAG 2.1 AA compliance
- Keyboard navigation throughout
- Screen reader compatibility
- Color contrast 4.5:1 minimum
- Focus indicators on all interactive elements

**Hidden features accessibility:**
- All capability-gated features still accessible
- Screen reader users can discover features
- Keyboard shortcuts for advanced users

---

## IMPLEMENTATION ROADMAP

### Phase 1: MVP (4-6 weeks)
**Surface features:**
- User registration/login
- Basic posting
- Friend connections (Ring 0/1)
- Simple messaging
- Profile pages

**Infrastructure:**
- PHP backend (portable)
- SQLite database (simple start)
- Server federation basics
- Basic encryption (Ring-to-Ring)

**Deliverable:** Functional social network, no gig marketplace yet

### Phase 2: Gig Marketplace (3-4 weeks)
**Features:**
- Gig posting/browsing
- Search and filters
- Messaging for gigs
- Basic payment tracking (manual)
- Reviews/ratings

**Dual use:**
- Steganographic encoding in gig fields
- Begin fragment storage testing

**Deliverable:** Social + economic platform

### Phase 3: Steganography Layer (4-6 weeks)
**Features:**
- Keystroke telemetry (opt-in)
- Photo filter signals
- Spam folder
- Gig decoder (hidden)

**Infrastructure:**
- Fragment storage system
- Reed-Solomon encoding
- Message reconstruction

**Deliverable:** Dual-use platform (90% innocent usage)

### Phase 4: Capability Injection (3-4 weeks)
**Features:**
- Phantom user system
- Social handshake verification
- Progressive feature unlocking
- Decoy ring redirect

**Security:**
- Infiltrator detection
- Honeypot monitoring
- Access logging

**Deliverable:** Secure onboarding, vetted users only

### Phase 5: Canary System (6-8 weeks)
**Features:**
- Dead man's switch
- Heartbeat monitoring
- Cascade release mechanism
- Compromised signaling

**Testing:**
- Simulated node seizures
- Network fragmentation tests
- Message reconstruction validation
- Suppression resistance drills

**Deliverable:** Full whistleblower haven

### Phase 6: Polish & Scale (Ongoing)
**UX improvements:**
- Onboarding optimization
- Performance tuning
- Mobile apps (native)
- Browser extensions

**Security hardening:**
- Penetration testing
- Cryptography audit
- Social engineering resistance
- Operational security training

---

## TECHNICAL STACK

### Backend
- **Language:** PHP 8.1+ (portable, widely hosted)
- **Framework:** Slim 4 (lightweight, flexible)
- **Database:** SQLite → PostgreSQL (as scale requires)
- **Encryption:** libsodium (built into PHP 7.2+)
- **File storage:** Local → S3-compatible (MinIO)

### Frontend
- **Framework:** Alpine.js (lightweight, progressive)
- **Build:** None initially (vanilla JS/CSS)
- **Later:** Vite (if complexity requires)
- **Icons:** Feather Icons (open source)
- **Fonts:** Inter (Google Fonts)

### Infrastructure
- **Hosting:** Shared hosting initially (PHP everywhere)
- **Federation:** HTTP + public/private key exchange
- **CDN:** Cloudflare (free tier, DDoS protection)
- **Monitoring:** Self-hosted (logs, metrics)

### Security
- **Crypto:** NaCl/libsodium (modern, audited)
- **Hashing:** Argon2id (password storage)
- **Randomness:** random_bytes() (CSPRNG)
- **TLS:** Let's Encrypt (free, automated)

---

## DEPLOYMENT STRATEGY

### Self-Hosting First
**Rationale:**
- Decentralization is core value
- Users can verify code
- No single point of failure
- Censorship resistance

**Installation:**
```bash
git clone https://github.com/maciejjankowski/osnova.git
cd osnova
php -S localhost:8000
# Visit http://localhost:8000
```

**Requirements:**
- PHP 8.1+
- SQLite3
- 512MB RAM minimum
- 1GB disk space

### Managed Hosting Option
**For non-technical users:**
- One-click install (Softaculous/Fantastico)
- Shared hosting compatible
- $5-10/month hosting cost
- Managed updates

### Federation
**Server discovery:**
- DNS-based (SRV records)
- Advertise via existing connections
- Web of trust model

**Inter-server protocol:**
- HTTPS + public key pinning
- Message format: JSON
- Encryption: per-ring keys
- Rate limiting: token bucket

---

## ECONOMICS & SUSTAINABILITY

### Revenue Streams

**1. Gig Marketplace Fee (Primary)**
- 5% platform fee on completed gigs
- $50 gig = $2.50 to platform
- Splits between servers based on ring topology
- Example: Your server hosts requester → gets 60%, provider's server gets 40%

**2. Premium Features (Optional)**
- Advanced analytics
- Larger file uploads
- Custom domains for profiles
- Priority support
- $3-5/month per user

**3. Server Hosting Service (Managed)**
- For non-technical users
- $10/month (includes hosting + updates)
- Platform takes $3, rest covers costs

**4. Enterprise/Activist Deployments**
- White-label installs
- Custom training
- Operational security consulting
- $1000-5000/deployment

### Cost Structure

**Per-user costs (at scale):**
- Hosting: $0.10/month
- Storage: $0.05/month  
- Bandwidth: $0.05/month
- Total: ~$0.20/month per active user

**Break-even:**
- With 5% gig fees: ~10 gigs/month per user
- With premium: ~1000 users at $5/month
- Sustainable at small scale

### Growth Strategy

**Phase 1: Activists & Whistleblowers (Months 1-6)**
- Target: Journalists, NGOs, dissidents
- Channel: Direct outreach, security conferences
- Goal: 1000 users, prove concept

**Phase 2: Freelancers & Gig Workers (Months 6-12)**
- Target: TaskRabbit/Fiverr refugees
- Channel: Content marketing, gig platforms
- Goal: 10,000 users, marketplace liquidity

**Phase 3: Privacy-Conscious Mainstream (Year 2)**
- Target: Threads/Twitter refugees
- Channel: Social media, PR, word of mouth
- Goal: 100,000 users, network effects

**Network effects trigger:** ~50,000 users
- Enough gig liquidity in major cities
- Ring topology becomes dense (useful connections)
- Whistleblower network has critical mass

---

## SECURITY CONSIDERATIONS

### Threat Actors

**1. State-level adversaries**
- Capabilities: Server seizure, network monitoring, legal pressure
- Mitigations: Decentralization, cascade release, jurisdiction diversity

**2. Corporate surveillance**
- Capabilities: Data purchase, infiltration, subpoena
- Mitigations: No central database, encryption, no third-party tracking

**3. Social engineering**
- Capabilities: Fake users, trust exploitation, phishing
- Mitigations: Social handshake, phantom users, decoy rings

**4. Cryptographic attacks**
- Capabilities: MITM, key compromise, protocol weaknesses
- Mitigations: Audited libraries (libsodium), perfect forward secrecy

### Attack Scenarios & Defenses

**Scenario: Government seizes primary server**
- Defense: Federation = users migrate to other servers
- Data loss: Minimal (encrypted, users hold keys)
- Canary messages: Already distributed, seizure triggers release

**Scenario: Infiltrator joins network**
- Defense: Social handshake verification
- If detected: Redirected to decoy ring
- Intel gained: Attacker tactics (honeypot value)

**Scenario: Sophisticated suppression (1000+ node seizure)**
- Defense: Exponential cost, 24h window impossible
- Outcome: Some messages still propagate
- Strategic: Public attention = Streisand effect

**Scenario: Cryptographic backdoor discovered**
- Defense: Open source, auditable
- Response: Server updates, key rotation
- Message survivability: Fragments already distributed

### Operational Security

**For users:**
- Documentation: Security best practices
- Training: Heartbeat discipline, duress signals
- Tools: Dead man's switch testing

**For operators:**
- Server hardening guides
- Incident response playbooks
- Backup procedures

**For developers:**
- Code review requirements
- Cryptography audit schedule
- Penetration testing

---

## SUCCESS METRICS

### Surface Layer (Social Network)
- Daily Active Users (DAU)
- Post engagement rate
- Gig completion rate
- User retention (30-day)
- Time spent in app

### Economic Layer (Marketplace)
- Gigs posted per day
- Gig completion rate
- Average gig value
- Platform fee revenue
- Repeat transactions

### Security Layer (Whistleblower)
- Successful canary tests (simulated)
- Message reconstruction time
- Fragment distribution coverage
- Infiltrator detection rate
- Zero successful suppressions

### Network Health
- Server count (federation)
- Average ring density
- Geographic distribution
- Jurisdiction diversity
- Uptime (99.5% target)

---

## CONCLUSION

Osnova is architecturally complete. Every layer serves dual purpose:

**Social features** create cover for **security capabilities**.  
**Gig marketplace** provides **steganographic containers**.  
**Innocent UX patterns** mask **whistleblower infrastructure**.  
**Fun, engaging platform** ensures **plausible deniability**.

**The genius:** 90% of users may never know the deep layer exists. They just enjoy a privacy-respecting social network with economic utility.

The remaining 10% have access to the most censorship-resistant whistleblower platform ever built.

**Ready for implementation.**

---

**Next step:** Build Phase 1 MVP.

