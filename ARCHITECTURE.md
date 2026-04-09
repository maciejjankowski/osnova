# Osnova Architecture: Modular Separation

## Core Principle
Osnova operates as TWO systems in ONE codebase:
1. **CORE** - Standard social network (gig economy + rings + messaging)
2. **WHISTLEBLOWER** - Activated only after specific behavioral triggers

## Directory Structure

```
osnova/
├── php/
│   ├── core/              # Always loaded - standard social features
│   │   ├── api/          # Public API endpoints
│   │   ├── lib/          # Core libraries
│   │   └── templates/    # Standard UI
│   │
│   ├── extensions/        # Conditionally loaded - whistleblower features
│   │   ├── canary/       # Canary system
│   │   ├── stego/        # Steganographic channels
│   │   ├── signals/      # Meta-signaling
│   │   └── phantom/      # Phantom users & capability gates
│   │
│   ├── loader.php        # Extension activation logic
│   └── index.php         # Main router
```

## Activation Model

### Core (Always Active)
- Posts, comments, reactions
- Ring formation and management
- Direct messaging
- Gig marketplace
- Profile management
- Discovery feed
- Bounty system

### Extensions (Conditionally Active)
Triggered by:
- Specific user presence in ring
- Behavioral patterns (typo frequency, emoji usage)
- Social handshake completion
- Phantom user follows
- Server capability negotiation
- Client-side extension installation

## Separation Strategy

### 1. File Organization
```
core/api/posts.php       → Standard posting
extensions/canary/api/   → Canary operations
```

### 2. Feature Flags
```php
// loader.php checks:
- User behavioral profile
- Ring composition
- Server capabilities
- Client extensions present
```

### 3. Database Schema
```sql
-- Core tables (always present)
posts, rings, members, messages, gigs, bounties

-- Extension tables (created on-demand)
canary_messages, shard_storage, release_triggers
keystroke_logs, phantom_users, capability_grants
```

### 4. API Endpoints
```
/api/posts          → Core (always)
/api/canary/*       → Extension (conditional 404 if not activated)
/api/stego/*        → Extension (conditional 404)
```

### 5. Client-Side Loading
```javascript
// core.js - always loaded
// If extensions activated:
//   - Load stego.js
//   - Load keystroke_monitor.js
//   - Load capability_injector.js
```

## Behavioral Triggers

### Activation Conditions (AND logic)
1. User follows phantom account
2. Performs social handshake (mentions "leo" or "manual")
3. Ring contains ≥1 trusted node
4. Client accepts "cookie policy" (actually capability grant)
5. Behavioral pattern matches (typo rate, emoji sequence)

### Infiltrator Detection
- Missing handshake → Redirect to decoy
- Wrong phantom follow → Limited ring visibility
- Behavioral mismatch → Standard features only
- No extension present → Server-side limitations

## Implementation Priority

### Phase 1: Core Separation
1. Move canary_* files to extensions/canary/
2. Move stego_* files to extensions/stego/
3. Create loader.php with activation logic
4. Update index.php to conditionally require extensions

### Phase 2: Activation Gates
1. Implement behavioral profiling
2. Create phantom user system
3. Add social handshake detection
4. Build capability negotiation

### Phase 3: Decoy Layer
1. Decoy servers for infiltrators
2. Limited functionality paths
3. Plausible deniability UX

## Security Properties

1. **Deniability**: Core looks like standard social network
2. **Separation**: Extensions invisible until activated
3. **Detection**: Infiltrators get decoy experience
4. **Compartmentalization**: Each extension independent
5. **Graceful degradation**: Missing extensions = normal user experience

## Next Steps

1. Create directory structure
2. Move files into core/ and extensions/
3. Build loader.php with simple activation (phantom user follow)
4. Test both modes (core-only vs full-featured)
5. Document activation sequences

---

**Critical**: Extensions MUST be invisible to:
- Web crawlers
- Uninvited users
- Infiltrators
- Casual inspection of codebase
