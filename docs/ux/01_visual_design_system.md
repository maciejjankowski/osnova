# Osnova Visual Design System
**Making Truth Beautiful**

---

## DESIGN PHILOSOPHY

### **Core Principles:**

1. **Clarity Over Cleverness**
   - Information hierarchy is obvious
   - No mystery meat navigation
   - Every element has a purpose

2. **Calm Technology**
   - Not competing for attention
   - Supports thought, doesn't hijack it
   - Respects user's time

3. **Trust Through Transparency**
   - Show system status (rings, propagation)
   - No hidden algorithms
   - Honest about what's happening

4. **Delight in Details**
   - Micro-animations celebrate wins
   - Thoughtful empty states
   - Personality without noise

---

## COLOR SYSTEM

### **Primary Palette:**

```
CORE Ring:    #2563EB (Blue 600)    - Trust, intimacy
INNER Ring:   #10B981 (Green 500)   - Growth, friends
MIDDLE Ring:  #F59E0B (Amber 500)   - Warmth, community
OUTER Ring:   #8B5CF6 (Violet 500)  - Discovery, public

Background:   #FFFFFF (White)        - Clean, honest
Surface:      #F9FAFB (Gray 50)     - Subtle depth
Border:       #E5E7EB (Gray 200)    - Definition
Text:         #111827 (Gray 900)    - Readable
Text Muted:   #6B7280 (Gray 500)    - Hierarchy
```

### **Semantic Colors:**

```
Success:      #10B981 (Green 500)
Warning:      #F59E0B (Amber 500)
Error:        #EF4444 (Red 500)
Info:         #3B82F6 (Blue 500)

Canary Armed:  #10B981 (Green 500)
Canary Trigger: #EF4444 (Red 500)
```

### **Why These Colors?**

- **Blue (CORE):** Psychology of trust + intimacy
- **Green (INNER):** Growth, positive relationships
- **Amber (MIDDLE):** Warmth without aggression
- **Violet (OUTER):** Creative, explorative
- **No black backgrounds:** Honest, not hiding anything
- **High contrast:** Accessibility (WCAG AAA)

---

## TYPOGRAPHY

### **Font Stack:**

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 
             'Segoe UI', system-ui, sans-serif;

--font-mono: 'JetBrains Mono', 'SF Mono', 'Consolas', 
             'Liberation Mono', monospace;
```

### **Type Scale:**

```css
--text-xs:   0.75rem   (12px)  - Timestamps, metadata
--text-sm:   0.875rem  (14px)  - Captions, labels
--text-base: 1rem      (16px)  - Body text, posts
--text-lg:   1.125rem  (18px)  - Emphasis
--text-xl:   1.25rem   (20px)  - Post previews
--text-2xl:  1.5rem    (24px)  - Section headers
--text-3xl:  1.875rem  (30px)  - Page headers
--text-4xl:  2.25rem   (36px)  - Hero text
```

### **Font Weights:**

```css
--font-normal:   400  - Body text
--font-medium:   500  - Labels, UI elements
--font-semibold: 600  - Emphasis, headers
--font-bold:     700  - Strong emphasis
```

### **Line Heights:**

```css
--leading-tight:  1.25  - Headlines
--leading-normal: 1.5   - Body text
--leading-relaxed: 1.75 - Long-form content
```

---

## SPACING SYSTEM

```css
--space-1:  0.25rem   (4px)
--space-2:  0.5rem    (8px)
--space-3:  0.75rem   (12px)
--space-4:  1rem      (16px)
--space-5:  1.25rem   (20px)
--space-6:  1.5rem    (24px)
--space-8:  2rem      (32px)
--space-10: 2.5rem    (40px)
--space-12: 3rem      (48px)
--space-16: 4rem      (64px)
```

**Rule:** Use multiples of 4px for consistency

---

## COMPONENT LIBRARY

### **1. Button Styles**

```css
/* Primary Action */
.btn-primary {
  background: var(--ring-core-color);
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 500;
  transition: all 150ms ease;
}

.btn-primary:hover {
  background: #1D4ED8; /* Darker blue */
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

/* Secondary Action */
.btn-secondary {
  background: white;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 500;
}

/* Ghost (subtle) */
.btn-ghost {
  background: transparent;
  color: var(--text-muted);
  padding: 0.5rem 1rem;
}

.btn-ghost:hover {
  background: var(--surface-color);
}
```

### **2. Post Card**

```css
.post-card {
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  padding: 1.5rem;
  margin-bottom: 1rem;
  transition: border-color 150ms ease;
}

.post-card:hover {
  border-color: var(--ring-core-color);
}

.post-card--core {
  border-left: 3px solid var(--ring-core-color);
}

.post-card--inner {
  border-left: 3px solid var(--ring-inner-color);
}
```

### **3. Ring Indicator**

```css
.ring-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.ring-badge--core {
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
}

.ring-badge--inner {
  background: rgba(16, 185, 129, 0.1);
  color: #10B981;
}
```

### **4. Avatar**

```css
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid white;
  box-shadow: 0 0 0 1px var(--border-color);
}

.avatar--small { width: 32px; height: 32px; }
.avatar--large { width: 64px; height: 64px; }
```

### **5. Input Fields**

```css
.input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: all 150ms ease;
}

.input:focus {
  outline: none;
  border-color: var(--ring-core-color);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.textarea {
  min-height: 120px;
  resize: vertical;
  font-family: inherit;
}
```

---

## LAYOUT PATTERNS

### **Main App Structure**

```
┌──────────────────────────────────────┐
│  Header (fixed)                      │
├──────┬───────────────────────┬───────┤
│ Side │   Main Feed           │ Side  │
│ Nav  │   (scrollable)        │ Info  │
│      │                       │       │
│ 240px│   600px max-width     │ 300px │
└──────┴───────────────────────┴───────┘
```

### **Mobile Layout**

```
┌───────────────┐
│ Header        │
├───────────────┤
│               │
│ Main Feed     │
│ (full width)  │
│               │
├───────────────┤
│ Bottom Nav    │
└───────────────┘
```

---

## ANIMATION PRINCIPLES

### **Micro-interactions:**

```css
/* Hover states: 150ms */
transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);

/* Page transitions: 300ms */
transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);

/* Celebration (confetti, success): 500ms */
transition: all 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
```

### **When to Animate:**

✅ **DO animate:**
- Button hover/click
- Post appearing in feed
- Success confirmation
- Ring selection
- Navigation transitions

❌ **DON'T animate:**
- Initial page load (too slow)
- Typing/input (distracting)
- Reading content (annoying)
- Bulk actions (overwhelming)

---

## ICONOGRAPHY

### **Icon System: Lucide Icons**
- Consistent stroke width (2px)
- 24×24px default size
- Monochrome (inherit text color)
- Outlined style (not filled)

### **Key Icons:**

```
Home:        home
Profile:     user
Post:        edit-3
Search:      search
Rings:       users
DM:          message-circle
Settings:    settings
Canary:      shield-alert (hidden until needed)
More:        more-horizontal
```

---

## RESPONSIVE BREAKPOINTS

```css
--mobile:     0px - 639px
--tablet:     640px - 1023px
--desktop:    1024px - 1279px
--wide:       1280px+
```

### **Mobile-First Approach:**

```css
/* Base styles = mobile */
.post-card {
  padding: 1rem;
}

/* Tablet+ */
@media (min-width: 640px) {
  .post-card {
    padding: 1.5rem;
  }
}

/* Desktop+ */
@media (min-width: 1024px) {
  .post-card {
    padding: 2rem;
  }
}
```

---

## ACCESSIBILITY

### **Requirements:**

✅ **WCAG AAA** color contrast (7:1 minimum)
✅ **Keyboard navigation** for all interactions
✅ **Screen reader** labels on all interactive elements
✅ **Focus indicators** visible and obvious
✅ **Skip links** for main content
✅ **Reduced motion** respect `prefers-reduced-motion`

### **Example:**

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## DARK MODE (Future)

```css
@media (prefers-color-scheme: dark) {
  :root {
    --background: #0F172A;  /* Slate 900 */
    --surface: #1E293B;     /* Slate 800 */
    --border: #334155;      /* Slate 700 */
    --text: #F1F5F9;        /* Slate 100 */
    --text-muted: #94A3B8;  /* Slate 400 */
  }
}
```

**Note:** Ship light mode first. Add dark mode in v2 after UX validated.

---

## COMPARISON TO COMPETITORS

| Element | Threads | Twitter | Mastodon | **Osnova** |
|---------|---------|---------|----------|------------|
| **Primary color** | Instagram gradient | Blue | Purple | Ring-based (4 colors) |
| **Typography** | Instagram Sans | Chirp | System | Inter (clean, readable) |
| **Buttons** | Rounded, flat | Rounded, filled | Sharp, 3D | Soft rounded, hover lift |
| **Feed density** | Loose | Tight | Very tight | Balanced |
| **Empty states** | Generic | None | Text-only | Helpful illustrations |
| **Animations** | Heavy (Instagram) | Minimal | None | Purposeful |

---

## PERSONALITY PRINCIPLES

### **Voice & Tone:**

**We are:**
- ✅ Honest, not corporate
- ✅ Calm, not anxious
- ✅ Helpful, not prescriptive
- ✅ Human, not robotic

**We are NOT:**
- ❌ Snarky/sarcastic
- ❌ Overly technical
- ❌ Preachy about privacy
- ❌ Trying to be funny

### **Example Microcopy:**

**GOOD:**
- "Post to CORE (5 close friends)"
- "Your data lives on your server"
- "See posts in order, no algorithm"

**BAD:**
- "Leverage ring topology for granular access control"
- "Decentralized peer-to-peer gossip protocol"
- "Big Tech HATES this!"

---

## LOADING STATES

```css
/* Skeleton loading (better than spinners) */
.skeleton {
  background: linear-gradient(
    90deg,
    #F3F4F6 25%,
    #E5E7EB 50%,
    #F3F4F6 75%
  );
  background-size: 200% 100%;
  animation: loading 1.5s ease-in-out infinite;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## NEXT: WIREFRAMES

Now that design system is established:
1. 🎯 Wireframe onboarding flow
2. 🎯 Wireframe main app screens
3. 🎯 High-fidelity mockups
4. 🎯 Interactive prototype
5. 🎯 User testing

---

*Design system complete. Moving to wireframes.*
