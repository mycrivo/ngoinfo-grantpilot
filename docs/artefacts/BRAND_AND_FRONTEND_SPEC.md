# BRAND_AND_FRONTEND_SPEC.md

Status: LOCKED – AUTHORITATIVE  
Version: 2.0  
Scope: Frontend Build + Transactional Email System  
Applies To:
- grantpilot.ngoinfo.org (Next.js frontend)
- ngoinfo.org (WordPress marketing)
- Transactional emails (Resend)
- Lifecycle emails
- Paid media assets

This document contains ONLY implementation-grade instructions.
No conceptual language.
No interpretative tone rules.
No marketing philosophy.

All instructions must be treated as deterministic build constraints.

---

# 0. GLOBAL BRAND ASSET RULES

## 0.1 Logo Source (MANDATORY)

ALWAYS load logo from:

https://ngoinfo.org/wp-content/uploads/2026/02/ngoinfo_logo_new.webp

Rules:
- Do NOT embed base64 version
- Do NOT copy locally
- Use external URL reference
- Logo may be resized via CSS
- Maintain aspect ratio
- Never crop
- Never recolor

Minimum logo height in header:
- 32px (mobile)
- 40px (desktop)

---

# 1. DESIGN TOKEN SYSTEM (LOCKED)

All frontend builds MUST use these tokens.

## 1.1 Colours

Primary:
--color-primary: #1A1F71;

Primary Hover:
--color-primary-hover: #141A5A;

Accent Gradient Start:
--color-accent-start: #5B2EFF;

Accent Gradient End:
--color-accent-end: #8B5CFF;

Coral Action:
--color-action: #FF6B4A;

Workspace Background:
--color-app-bg: #F8F9FC;

Card Background:
--color-card-bg: #FFFFFF;

Border:
--color-border: #E5E7EB;

Divider:
--color-divider: #F1F3F8;

Success:
--color-success: #059669;

Warning:
--color-warning: #D97706;

Error:
--color-error: #DC2626;

Neutral:
--color-neutral: #475569;

Primary Text:
--color-text-primary: #374151;

Secondary Text:
--color-text-secondary: #6B7280;

---

# 2. TYPOGRAPHY (LOCKED)

Font Family:
'DM Sans', -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;

Google Import:
DM Sans
Weights: 400, 500, 600, 700

Root font-size: 16px

## Heading Scale

H1:
48px / 56px
700 weight
color: #1A1F71

H2:
32px / 40px
700 weight
color: #1A1F71

H3:
24px / 32px
600 weight
color: #1A1F71

H4:
20px / 28px
600 weight
color: #111827

## Body

Primary:
16px / 24px
400 weight
#374151

Secondary:
14px / 20px
#6B7280

Minimum allowed text size:
14px

---

# 3. SPACING SYSTEM

8px grid only.

Allowed spacing increments:
4px
8px
16px
24px
32px
48px
64px

Card padding:
24px

Card radius:
12px

Shadow:
0px 4px 12px rgba(0,0,0,0.05)

---

# 4. BUTTON SYSTEM

Primary Button:
background: #1A1F71
color: #FFFFFF
padding: 14px 24px
radius: 8px
font-weight: 600
font-size: 16px

Hover:
#141A5A

Upgrade Button:
background: linear-gradient(135deg, #5B2EFF 0%, #8B5CFF 100%)
color: #FFFFFF

Secondary Button:
border: 1px solid #1A1F71
color: #1A1F71
background: transparent

---

# 5. FRONTEND BUILD REQUIREMENTS

## 5.1 Visual Match Requirement

GrantPilot frontend MUST visually align with:

https://ngoinfo.org/n1

Alignment requirements:
- Same primary navy
- Same DM Sans
- Same gradient style
- Same rounded corner system
- Same button visual weight
- Same header layout logic

GrantPilot is a workspace variant of n1.
Not a marketing site clone.
But must look like same brand family.

---

## 5.2 Layout Rules

Header:
- White background
- Logo left
- Minimal nav
- No heavy gradients

App pages:
- Light workspace background (#F8F9FC)
- White cards
- Clear hierarchy
- No decorative shapes
- No marketing-style backgrounds

---

# 6. STATUS COLOUR ENFORCEMENT (PRODUCT)

Mapping is deterministic.

RECOMMENDED → #059669  
APPLY_WITH_CAVEATS → #D97706  
NOT_RECOMMENDED → #DC2626  

Do NOT invent alternative colour tones.

---

# 7. TRANSACTIONAL EMAIL SYSTEM (LOCKED)

Provider: Resend

All transactional emails must:

- Use 600px max container
- Background: #F8F9FC
- Inner card: #FFFFFF
- Logo top (from canonical URL)
- Primary CTA color: #1A1F71
- Font: DM Sans

No gradient in emails.

---

## 7.1 Required Email Templates

1. Welcome Email
2. Magic Link Email
3. Fit Scan Completed
4. Proposal Generated
5. Quota Exhausted
6. Subscription Activated
7. Subscription Renewal
8. Subscription Cancelled
9. Payment Failed

---

## 7.2 Email Content Constraints (Deterministic)

Email text MUST NOT include:

- “win more grants”
- “increase your chances”
- “guaranteed”
- “success probability”
- “AI-powered intelligence engine”

Email text MAY include:

- “structured assessment”
- “alignment analysis”
- “proposal draft”
- “review before submission”
- “eligibility review”

These strings must be validated during review.

---

# 8. COMPLIANCE LANGUAGE FILTER (FOR AI TOOLS)

When generating content, the following regex patterns MUST NOT appear:

/(win|winning)\s+grants/i
/probability/i
/guarantee/i
/increase\s+your\s+chances/i
/high\s+chance/i

These must be treated as blocked phrases.

---

# 9. ACCESSIBILITY REQUIREMENTS

Minimum contrast ratio:
4.5:1

Minimum button height:
44px

Focus states required.

---

# 10. VERSION CONTROL

If any colour, font, spacing, button system or email layout changes:
- Update this file
- Increment version
- Document change log

No silent modifications allowed.

---

END OF DOCUMENT
