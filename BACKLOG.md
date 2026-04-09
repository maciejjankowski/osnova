# OSNOVA - Decentralized Truth Network
> Backlog maintained by Oracle. Updated after each agent completes a deliverable.
> Spec: SPEC.md (complete dual-use social network + whistleblower haven)

## STATUS: PRODUCTION READY
- **Phase 1 (UX Layer):** COMPLETE ✅
- **Phase 2 (Steganography):** COMPLETE ✅
- **Phase 3 (Canary System):** COMPLETE ✅
- 195 tests passing (Python - integration validated)
- Full PHP implementation with all SPEC.md features
- Live deployment: https://va.evil1.org

**Latest updates (2026-04-09):**
- Full UX layer with onboarding flow
- Design system (Osnova.css) - mobile-first, accessible
- Gig marketplace (social + economic)
- Steganography layer (keystroke telemetry, capabilities, spam folder)
- Canary whistleblower system (dead man's switch, cascade release)
- 15+ new features in one session

---

## DONE

### Phase 1: UX & Social Layer (2026-04-09) ✅
- [x] Design system (Osnova.css) - Threads-competitive styling
- [x] Onboarding flow (4-step wizard: welcome, identity, invite, tour)
- [x] Gig marketplace API + storage (SQLite)
- [x] Gig posting and browsing templates
- [x] Ring-based visibility controls
- [x] Mobile-first responsive design (WCAG 2.1 AA)
- [x] Messages system with inbox

### Phase 2: Steganography Layer (2026-04-09) ✅
- [x] Keystroke telemetry (meta-message extraction)
- [x] Progressive capability unlocking
- [x] Phantom user system for feature gates
- [x] Spam folder as secure channel
- [x] Profile filter signals
- [x] Gig decoder for steganographic containers
- [x] Context-triggered capability injection
- [x] Capabilities API

### Phase 3: Canary Whistleblower System (2026-04-09) ✅
- [x] Dead man's switch with heartbeat monitoring
- [x] Message fragmentation (Reed-Solomon distribution)
- [x] Fragment storage across rings (30%/40%/30%/20%)
- [x] Cascade release mechanism
- [x] Compromised signal handling
- [x] Message reconstruction from 60%+ fragments
- [x] Canary composer UI (capability-gated)
- [x] Cron job for automated monitoring

### Foundation (2026-04-08 and earlier)
- [x] Project structure + pyproject.toml + venv
- [x] Data models (schemas.py) - all content, peer, signal, discovery schemas
- [x] Identity module (crypto/identity.py) - Ed25519 keypair, sign, verify - 19 tests
- [x] Storage module (storage/log.py) - SQLite append-only log - 15 tests
- [x] Ring management (rings/manager.py) - Dunbar-capped trust rings - 21 tests
- [x] Gossip protocol (gossip/sync.py) - pull-based HTTP sync - 16 tests

### Phase 2: Core Features
- [x] FastAPI endpoints (api/routes.py) - 20+ API endpoints - 33 tests
- [x] Node eject protocol (eject/protocol.py) - package, eject, reattach, canary - 21 tests
- [x] Riddle encoder integration (integrity/riddle.py) - CSP encoding + verification - 23 tests
- [x] Triangulated discovery (discovery/triangulation.py) - message/countermessage/challenge - 32 tests

### Phase 3: Integration
- [x] Discovery API endpoints + frontend page - 10 tests
- [x] Signature verification middleware (api/middleware.py)
- [x] HTMX frontend - 9 templates (feed, compose, rings, identity, eject, discover)
- [x] Multi-node integration tests - 5 tests (real processes, real HTTP)
- [x] README.md + cluster launcher script

---

## NEXT STEPS (ordered by value, no Docker)

### Near-term (extend what exists)
- [x] **PARDES metadata auto-tagging** - tag content with PARDES layer info at creation ✅ 2026-04-08
- [x] **Middle ring content filtering** - only replicate SEEDs/PARAGRAPHs to middle ring peers ✅ 2026-04-08
- [x] **Persistent signals + triads** - store in SQLite instead of in-memory lists ✅ 2026-04-08
- [x] **Context hints with domain vocabulary** - wire Lynchpin noise vocabulary into challenge hints ✅ 2026-04-08
- [x] **Discovery distribution automation** - auto-split and send keys to ring peers on triad creation ✅ 2026-04-08
- [x] **Canary trap detection** - track which challenges get resolved incorrectly (reveals outsiders) ✅ 2026-04-08

### Medium-term (new capabilities)
- [x] **Credibility flagging** - flag questionable content, seek more context ✅ 2026-04-08
- [x] **Ephemeral content** - TTL-based auto-purge honored by ring members ✅ 2026-04-08
- [x] **Polls + quadratic voting** - per-ring democratic tools ✅ 2026-04-08
- [x] **Liquid delegation** - delegative voting within trust rings ✅ 2026-04-08
- [x] **Bounty system** - information requests with path-attributed rewards (Shapley values) ✅ 2026-04-08
- [x] **Key rotation** - threshold signatures (k-of-n inner ring co-sign) ✅ 2026-04-08
- [ ] **IPFS transport** - content-addressable storage via libp2p (external dep)

### Long-term (resilience layer)
- [ ] **LoRa/Meshtastic transport** - SEED-only propagation over radio
- [ ] **Bluetooth mesh** - local cluster communication
- [ ] **Packet radio (AX.25)** - last-resort transport
- [ ] **Store-carry-forward (DTN)** - delay-tolerant networking
- [ ] **DHT peer discovery** - Kademlia variant for beyond-Dunbar discovery
- [ ] **Cross-ring linking** - inter-community connections with mutual approval
- [ ] **Bounty algorithm A/B testing** - experiment framework for incentive curves
- [ ] **Mobile PWA** - responsive progressive web app

### Research (parallel track)
- [ ] **CSP complexity proof** - prove riddle encoding inversion is NP-hard
- [ ] **PARDES as error-correcting code** - formalize holographic 3-of-5 reconstruction
- [ ] **Study SSB failure modes** - why Scuttlebutt didn't scale, what to avoid
- [ ] **Shapley value computation** - efficient algorithms for bounty path attribution

---

## AGENT ROSTER

| Agent | Role | Status |
|-------|------|--------|
| ARCHITECT | Structure, schemas, backlog | DONE |
| DEV-CRYPTO | Identity, signing | DONE (19 tests) |
| DEV-STORAGE | SQLite log | DONE (15 tests) |
| DEV-RINGS | Trust rings | DONE (21 tests) |
| DEV-GOSSIP | Peer sync | DONE (16 tests) |
| DEV-API | FastAPI endpoints | DONE (33 tests) |
| DEV-EJECT | Eject + canary | DONE (21 tests) |
| DEV-RIDDLE | Riddle encoder | DONE (23 tests) |
| DEV-DISCOVERY | Triangulated discovery | DONE (32 tests) |
| DEV-INTEGRATION | API wiring + middleware + discovery API | DONE (10 tests) |
| DEV-MULTINODE | Integration tests | DONE (5 tests) |
| DEV-UI | HTMX frontend | DONE |
| DEV-DOCS | README + launcher | DONE |

---

*Last updated: 2026-04-08 by Oracle - Near-term (6/6) + Medium-term (6/7) complete. 12 features in one day. IPFS deferred (external dep).*
