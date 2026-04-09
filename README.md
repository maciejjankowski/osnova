# Osnova - Social Network meets Whistleblower Haven

**A dual-use decentralized platform:** Engaging social network + gig marketplace on the surface. Military-grade censorship-resistant whistleblower network underneath.

**Status:** Production Ready (Phase 1-3 complete)  
**Live Demo:** https://va.evil1.org  
**Full Specification:** [SPEC.md](SPEC.md)

---

## Why Osnova?

90% of users get a privacy-respecting social network with economic utility.  
10% who need it get the most censorship-resistant whistleblower platform ever built.

### For Everyone:
- 👥 **Ring-based social network** - Control who sees what (Ring 0-3)
- 💼 **Gig marketplace** - Earn money helping your network
- 🔒 **Encrypted by default** - No corporate tracking
- 📱 **Mobile-first design** - Works everywhere
- 🌐 **Decentralized** - No single point of failure

### For Whistleblowers:
- 🕊️ **Dead man's switch** - Auto-release if you disappear
- 🧩 **Message fragmentation** - Distributed across 100+ pieces
- 🔄 **Cascade release** - Exponentially resistant to suppression
- 🎭 **Plausible deniability** - Every feature has dual purpose
- 🛡️ **Phantom users** - Social handshake authentication

---

## Quick Start

### Installation

```bash
git clone https://github.com/maciejjankowski/osnova.git
cd osnova/php
php -S localhost:8000
```

Visit `http://localhost:8000` - that's it!

**Requirements:** PHP 8.1+, SQLite3, 512MB RAM

### First Run

1. Visit `/welcome` for onboarding
2. Create your identity (client-side keypair)
3. Optional: Enter invite code to join a ring
4. Start exploring!

---

## Architecture

### Layer 1: Social Network (Surface)
Standard social media features:
- Post feed with ring visibility
- Friend connections
- Direct messages
- Profile customization

### Layer 2: Gig Marketplace
TaskRabbit/Fiverr hybrid:
- Post gigs with ring-scoped visibility
- Browse and complete tasks
- 5% platform fee split across federated servers
- **Hidden:** Gigs double as steganographic containers

### Layer 3: Steganographic Signals
Every innocent feature has a covert purpose:
- **Keystroke telemetry** ("improving autocorrect") → meta-messages
- **Profile photo filters** → status signals
- **Spam folder** → secure channel
- **Gig postings** → fragment storage
- **App update prompts** → capability injection

### Layer 4: Capability Injection
Features unlock based on context:
- **Phantom users** in your ring → unlock advanced features
- **Social handshake** → verbal invite codes
- **Progressive disclosure** → natural feature discovery
- **Decoy rings** → redirect infiltrators

### Layer 5: Whistleblower Canary
Military-grade survivability:
- **Heartbeat monitoring** (12h-72h intervals)
- **Message fragmentation** (Reed-Solomon distribution)
- **Cascade release** across rings on disappearance
- **Compromised signal** for duress scenarios
- **60% reconstruction threshold** (works even if 40% of nodes seized)

---

## API Reference

### Core Endpoints

**Posts**
```
POST   /api/posts        - Create post
GET    /api/posts        - Get feed
```

**Rings**
```
POST   /api/rings/add    - Add peer to ring
GET    /api/rings        - List ring members
```

**Gigs**
```
POST   /api/gigs/post    - Post a gig
GET    /api/gigs/list    - Browse gigs
POST   /api/gigs/complete - Mark gig complete
```

**Messages**
```
POST   /api/messages/send  - Send message
GET    /api/messages/list  - Get inbox
GET    /api/messages/spam  - Get spam folder (capability-gated)
```

**Capabilities**
```
GET    /api/capabilities/check  - Check unlocked features
POST   /api/capabilities/unlock - Unlock capability
```

**Canary (Capability-Gated)**
```
POST   /api/canary/create       - Create dead man's switch
POST   /api/canary/heartbeat    - Record heartbeat
GET    /api/canary/status/:id   - Check canary status
POST   /api/canary/compromised  - Signal compromised
GET    /api/canary/reconstruct/:id - Reconstruct message
```

---

## Security Model

### Threat Actors

**1. State-level adversaries**
- Capabilities: Server seizure, network monitoring, legal pressure
- Mitigation: Decentralization, cascade release, jurisdiction diversity

**2. Corporate surveillance**
- Capabilities: Data purchase, infiltration, subpoena
- Mitigation: No central DB, encryption, no third-party tracking

**3. Social engineering**
- Capabilities: Fake users, trust exploitation
- Mitigation: Social handshake, phantom users, decoy rings

### Attack Resistance

**Scenario: Government seizes primary server**
- ✅ Users migrate to federated servers
- ✅ Canary messages already distributed
- ✅ Seizure triggers cascade release

**Scenario: Infiltrator joins network**
- ✅ Social handshake verification fails
- ✅ Redirected to decoy ring
- ✅ Gains no access to real fragments

**Scenario: Suppress entire Ring 0 (10 nodes)**
- ✅ Ring 1 (100 nodes) holds 40% of fragments
- ✅ Can still reconstruct message
- ✅ Attacker must suppress 100+ nodes in 24h

**Scenario: Suppress 1000+ nodes simultaneously**
- ✅ Exponential cost impossible to achieve
- ✅ Some nodes always survive
- ✅ Attempted suppression = Streisand effect

---

## Dual-Use Feature Matrix

| Innocent Feature | Covert Purpose | Trigger |
|-----------------|----------------|---------|
| Photo color filter | Signal status/mode | Phantom user in ring |
| Typos in messages | Meta-message channel | Pre-agreed patterns |
| Gig posting | Steganographic container | Price = fragment ID |
| Spam folder | Secure message channel | "Spam trainer" phantom user |
| Cookie consent | Capability injection | Ring composition |
| "App update" | Mode switch | Specific user online |
| Following inactive user | Feature gate unlock | User ID pattern |
| Emoji reactions | Voting mechanism | Reaction combinations |

---

## Capability Unlocking

### Ring 0 (New user):
- Basic posting
- Public gigs only
- Standard messaging

### Ring 1 (After first connection):
- Ring-limited posts
- Private gigs
- Group messages

### Ring 2 (After phantom user unlock):
- Spam folder
- Advanced gig search
- Telemetry opt-in

### Ring 3 (After social handshake):
- Full steganographic features
- Canary composer
- Fragment viewer
- Decoy detection

---

## Deployment

### Self-Hosting (Recommended)

**Simple:**
```bash
cd osnova/php
php -S localhost:8000
```

**Production (Apache):**
```apache
<VirtualHost *:80>
    DocumentRoot /var/www/osnova/php
    <Directory /var/www/osnova/php>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

**Canary Monitoring (Cron):**
```bash
# Check for missed heartbeats every hour
0 * * * * /path/to/osnova/php/scripts/canary_monitor.php
```

### Federation

Servers discover each other via:
- DNS SRV records
- Peer advertisements
- Web of trust model

Each server maintains its own ring topology and fragments.

---

## Economics

### Revenue Streams

1. **Gig marketplace fee:** 5% platform fee
   - Split: 60% requester's server, 40% provider's server
   
2. **Premium features:** $3-5/month
   - Advanced analytics
   - Larger uploads
   - Custom domains

3. **Managed hosting:** $10/month
   - For non-technical users
   
4. **Enterprise deployments:** $1000-5000
   - White-label installs
   - OpSec consulting

### Cost Structure

Per-user costs (at scale):
- Hosting: $0.10/month
- Storage: $0.05/month
- Bandwidth: $0.05/month
- **Total: ~$0.20/month**

Break-even: ~1000 users with premium or 10 gigs/user/month

---

## Development

### Tech Stack

**Backend:** PHP 8.1+ (portable, widely hosted)  
**Database:** SQLite → PostgreSQL (as scale requires)  
**Encryption:** libsodium (built into PHP 7.2+)  
**Frontend:** Alpine.js + vanilla JS/CSS  
**Design:** Osnova.css (mobile-first, WCAG 2.1 AA)

### Running Tests

**PHP:**
```bash
cd php
php tests/test_all.php
```

**Python (integration):**
```bash
cd osnova
pytest -v
```

### Contributing

1. Check [BACKLOG.md](BACKLOG.md) for current priorities
2. Read [SPEC.md](SPEC.md) for complete architecture
3. Test locally before submitting PR
4. All features must maintain dual-use principle

---

## Roadmap

### ✅ Phase 1: MVP (Complete)
- Social network core
- Ring topology
- Gig marketplace
- Onboarding flow

### ✅ Phase 2: Steganography (Complete)
- Keystroke telemetry
- Capability injection
- Spam folder
- Profile signals

### ✅ Phase 3: Canary System (Complete)
- Dead man's switch
- Message fragmentation
- Cascade release
- Heartbeat monitoring

### 🔄 Phase 4: Polish & Scale (Ongoing)
- Mobile apps (PWA)
- Browser extension
- Performance optimization
- Penetration testing

### 📋 Phase 5: Long-term Resilience
- IPFS transport
- LoRa/Meshtastic support
- Bluetooth mesh
- Store-carry-forward

---

## FAQ

**Q: Is this legal?**  
A: Yes. Osnova is a social network. Whistleblowing is protected in many jurisdictions. We don't host illegal content.

**Q: Can governments shut this down?**  
A: Individual servers, yes. The network, no. It's decentralized and federated. Shutting it down requires suppressing thousands of nodes simultaneously - economically impossible.

**Q: How is this different from Signal/Tor?**  
A: Signal requires both parties online. Tor has exit node vulnerabilities. Osnova uses dead man's switch with distributed fragment storage - works even if you're captured.

**Q: What if I just want to use it as a social network?**  
A: Perfect! 90% of users will never see the whistleblower features. You get a privacy-respecting social network with a gig marketplace.

**Q: Why PHP?**  
A: Portability. PHP runs on cheap shared hosting everywhere. Lowers barrier to entry for federation. No Node.js, Docker, or complex setup.

**Q: Is it production ready?**  
A: Core features are complete and tested. Polish and scale optimization ongoing. Use at your own risk for sensitive operations.

---

## License

MIT License - See [LICENSE](LICENSE) for details

---

## Credits

- **Architecture:** Based on Scuttlebutt, Secure Scuttlebutt, and modern whistleblower platforms
- **Design:** Inspired by Threads, Signal, and privacy-first applications
- **Cryptography:** libsodium (NaCl) for all crypto operations

---

## Support

- **GitHub:** [maciejjankowski/osnova](https://github.com/maciejjankowski/osnova)
- **Issues:** Use GitHub Issues for bugs and feature requests
- **Security:** Email security issues privately (see SECURITY.md)

---

**"The truth wants to be free. Osnova makes it unstoppable."**
