# Osnova UX Research Framework
**Dual-Use Social Network: Secure Communication + Whistleblower Haven**

---

## THE STRATEGIC TENSION

**TWO PERSONAS, ONE APP:**

### **Persona 1: The Social User (95% of users)**
- "I want better conversations than Twitter/Threads"
- "I'm tired of algorithm manipulation"
- "I want control over my data"
- **Doesn't care about whistleblowing (yet)**
- **Drives network effects**

### **Persona 2: The Whistleblower (5% of users)**
- "I need to get this truth out safely"
- "I might die/disappear if I speak"
- "I need plausible deniability"
- **Needs the crowd from Persona 1**
- **Drives mission/purpose**

---

## THE UX PARADOX

**If you optimize for whistleblowers:**
- Heavy security UX scares away social users
- "Why does my meme app need this?"
- Network dies from lack of users

**If you optimize for social:**
- Whistleblowers don't trust it
- "This looks like just another Twitter clone"
- Mission fails

**SOLUTION:** Progressive disclosure + Dual-track onboarding

---

## COMPETITIVE ANALYSIS

### **Threads (Meta)**
✅ Strengths:
- Instant Instagram integration
- Familiar UI (Twitter clone)
- Zero learning curve
- Fast, polished
- Network effects via Instagram

❌ Weaknesses:
- Algorithm manipulation
- No privacy
- Corporate censorship
- No edit, no chronological feed
- Zuckerberg

### **Twitter/X**
✅ Strengths:
- Network effects (everyone's there)
- Real-time conversation
- Cultural dominance
- Quote tweets, threads

❌ Weaknesses:
- Elon chaos
- Algorithm shows rage bait
- Bots everywhere
- Paid verification broken
- Dying culture

### **Mastodon**
✅ Strengths:
- Decentralized
- No corporate control
- Chronological feed
- Open source

❌ Weaknesses:
- Confusing onboarding ("pick a server?")
- Fragmented network
- Slow, clunky
- No quote posts (by design)
- Nerd-only appeal

### **Signal/Telegram**
✅ Strengths:
- E2E encryption
- Privacy-focused
- Simple messaging UX

❌ Weaknesses:
- NOT social network
- No public discourse
- No discovery
- Channels ≠ conversation

---

## OSNOVA'S COMPETITIVE EDGE

### **What We Can Do That They Can't:**

1. **Ring-Based Trust Architecture**
   - Threads: You're either public or private
   - Osnova: 4 layers of selective disclosure (CORE/INNER/MIDDLE/OUTER)
   - **UX benefit:** "Share with close friends without Instagram knowing"

2. **Disappearing Centralization**
   - Twitter/Threads: Corporate server owns everything
   - Mastodon: Pick a server, trust admin
   - Osnova: You ARE the server
   - **UX benefit:** "Your data lives on YOUR server"

3. **Anti-Algorithm Timeline**
   - Threads: What Meta wants you to see
   - Twitter: What Elon/algorithm wants you to see
   - Osnova: Chronological by ring, NO MANIPULATION
   - **UX benefit:** "See what your actual friends posted, in order"

4. **Whistleblower Insurance** (hidden feature)
   - Others: Delete = gone, platform can suppress
   - Osnova: Canary system makes truth unsuppressible
   - **UX benefit:** "Your important posts can't be memory-holed"

5. **No Ads, Ever**
   - Threads/Twitter: You are the product
   - Osnova: $2/year peer hosting
   - **UX benefit:** "No ads. No tracking. No bullshit."

---

## UX RESEARCH QUESTIONS

### **Q1: What's the hook? (First 10 seconds)**
- ❌ "Decentralized social network with ring topology"
- ❌ "Whistleblower-safe truth preservation system"
- ✅ "Twitter, but your friends actually see your posts"
- ✅ "Social media that doesn't manipulate you"

### **Q2: Why would I leave Twitter/Threads?**
- Algorithm rage → Chronological peace
- Corporate control → Self-sovereignty
- Data mining → Privacy by default
- Censorship → Unstoppable truth (for those who need it)

### **Q3: What's the first delightful moment?**
- Seeing "CORE ring: 5 people" (your actual friends)
- First post goes ONLY to them (not the world)
- "This feels like early Twitter"
- Discovery: Someone adds YOU to their ring

### **Q4: How do we hide complexity?**
- Don't say "ring topology" → Say "friend circles"
- Don't say "gossip protocol" → Say "your posts spread naturally"
- Don't say "Shamir secret sharing" → Say "your data is split across friends"
- Don't mention "whistleblower" in main flow → Feature for those who need it

### **Q5: What's the growth loop?**
1. User joins, invites 5 CORE friends
2. Posts something good
3. CORE friends share to INNER (15 people)
4. INNER shares to MIDDLE (50 people)
5. Network grows organically via actual engagement
6. No algorithm = quality over viral trash

---

## ONBOARDING RESEARCH (Best Practices)

### **Duolingo Model:**
✅ Start with WHY (gamification, streaks, fun)
✅ Immediate value (learn in 5 min/day)
✅ Progressive complexity (start easy)
✅ Celebration of wins (animations, sounds)

### **Slack Model:**
✅ "Channels" concept is familiar
✅ Invite team before first use
✅ Demo data shows what it looks like
✅ Guided tour with real actions

### **TikTok Model:**
✅ Instant content (no empty state)
✅ Show, don't tell
✅ Addictive first experience
✅ Algorithm learns from first 10 interactions

### **Signal Model:**
✅ Privacy without complexity
✅ "Just works" like regular messaging
✅ Advanced features hidden until needed
✅ Trust through simplicity

---

## OSNOVA ONBOARDING STRATEGY

### **Step 1: The Hook (10 seconds)**
```
Screen 1: 
"Twitter, but for actual humans"

[Visual: Twitter/Threads UI with angry algorithm crossed out]
[Visual: Osnova UI with friendly chronological feed]

Button: "Try it free"
```

### **Step 2: The Promise (30 seconds)**
```
Screen 2: Why Osnova?

✅ No algorithm (see what friends actually post)
✅ No ads (pay $2/year, not with your data)  
✅ No corporate censorship (you own your server)
✅ Friend circles (share with who you want)

Button: "Get started"
```

### **Step 3: Profile Creation (2 minutes)**
```
Screen 3: Create your identity

[Photo upload]
Display name: ___________
Bio: ___________

Optional: Link Twitter/Threads to find friends

Button: "Next"
```

### **Step 4: Seed Your Network (3 minutes)**
```
Screen 4: Build your CORE circle

Invite 5 close friends (the ones you actually talk to):

[Email input] [Send invite]
[Email input] [Send invite]
[Email input] [Send invite]

"Why 5? Studies show we can maintain ~5 deep friendships.
Your CORE circle is your real inner circle."

Button: "Skip for now" | "Next"
```

### **Step 5: First Post (Magical Moment)**
```
Screen 5: Make your first post

[Text box]
"What's on your mind?"

Share with:
🔵 CORE (5 people - your closest friends)
🟢 INNER (15 people - good friends)  
🟡 MIDDLE (50 people - friends)
⚪ OUTER (Everyone on Osnova)

[Default: CORE selected]

Button: "Post"

[Confetti animation when posted]
"🎉 Your first post! Only your 5 CORE friends will see this."
```

### **Step 6: Discovery**
```
Screen 6: Find interesting people

[Suggested based on:]
- Friends of friends
- Similar interests (from bio)
- Popular in your city/country

[Preview posts from each]

Button: "Add to INNER" | "Skip"
```

### **Step 7: Advanced Features (Hidden)**
```
Screen 7: Optional power features

[Collapsed sections - user can explore later]

📌 Pin important posts (canary system)
🔒 Encrypted DMs
📡 Export your data anytime
🌐 Cross-network federation

Button: "Start using Osnova"
```

---

## UX PRINCIPLES

### **1. Progressive Disclosure**
- Start simple (post to friends)
- Reveal complexity as needed (rings, canary, federation)
- Never force advanced features

### **2. Familiar, But Better**
- Looks like Twitter (familiar)
- Works like early Twitter (chronological)
- Feels better (no manipulation)

### **3. Defaults Matter**
- Default to CORE ring (privacy by default)
- Default to chronological (sanity by default)
- Default to simple (complexity opt-in)

### **4. Delight Over Features**
- Confetti when you post
- Notification when friend adds you to ring
- "Streak" if you post daily
- Discovery of like-minded people

### **5. Trust Through Transparency**
- Show who's in each ring
- Show how posts propagate
- Show where data is stored
- No hidden algorithms

---

## DUAL-TRACK ONBOARDING

### **Track A: Social User (95%)**
Flow: Hook → Promise → Profile → Network → First Post → Discovery → Done

**Never mentions:** Whistleblowing, canary, suppression-proof
**Highlights:** Friends, chronological, no algorithm, privacy

### **Track B: Whistleblower (5%)**
Entry point: "Need to protect important information?"

Flow: Security assessment → Canary setup → Ring distribution → Test → Armed

**Only accessible via:**
- Settings > Advanced > Truth Protection
- Direct link from trusted source
- After 30 days of normal use (trust earned)

---

## COMPETITIVE UX MATRIX

| Feature | Threads | Twitter | Mastodon | Signal | **Osnova** |
|---------|---------|---------|----------|--------|------------|
| **Easy onboarding** | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Chronological feed** | ❌ | ❌ | ✅ | N/A | ✅ |
| **No algorithm manipulation** | ❌ | ❌ | ✅ | N/A | ✅ |
| **Privacy by default** | ❌ | ❌ | ⚠️ | ✅ | ✅ |
| **Selective sharing** | ⚠️ | ⚠️ | ❌ | ✅ | ✅ |
| **Own your data** | ❌ | ❌ | ⚠️ | ⚠️ | ✅ |
| **Can't be suppressed** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Network effects** | ✅ | ✅ | ❌ | ⚠️ | 🎯 |
| **Fun to use** | ✅ | ⚠️ | ❌ | ❌ | 🎯 |

🎯 = Our target competitive advantage

---

## KEY INSIGHTS

### **1. Don't Lead with Technology**
- ❌ "Peer-to-peer gossip protocol with ring topology"
- ✅ "See what your friends actually posted, in order"

### **2. Don't Lead with Ideology**
- ❌ "Decentralized resistance to corporate surveillance"
- ✅ "Twitter, but the algorithm doesn't make you angry"

### **3. Lead with Emotion**
- Remember early Twitter? (Nostalgia)
- Tired of rage bait? (Relief)
- Want actual friends to see your posts? (Connection)

### **4. Hide the Whistleblower**
- It's there for those who need it
- But 95% of users just want good social media
- Let the network effects serve the mission

### **5. Threads Is the Target**
- New, so users aren't entrenched
- Already leaving Twitter (Elon chaos)
- Instagram users want alternative
- Algorithm fatigue is REAL
- We can be "Threads, but honest"

---

## NEXT STEPS

1. ✅ Research complete
2. 🎯 Wireframe key screens
3. 🎯 Design system (colors, typography, components)
4. 🎯 Interactive prototype
5. 🎯 User testing (5-10 people)
6. 🎯 Iterate based on feedback
7. 🎯 Build production UI
8. 🎯 A/B test onboarding flow

---

*Framework complete. Moving to wireframes and visual design.*
