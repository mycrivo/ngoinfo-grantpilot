# NGOInfo Brand Guidelines

Status: Authoritative for NGOInfo marketing UI builds  
Scope: `ngoinfo.org` marketing pages, funding opportunity pages, pricing pages, landing pages, CTA sections, footer, and WordPress-facing frontend work  
Use with Cursor: Reference this file directly in all frontend build prompts. Do not re-explain brand rules in prompts.

---

## 0. Cursor Governance Rules

Cursor must follow this file for all NGOInfo marketing frontend work.

Before coding, Cursor must also check any project-level authoritative files relevant to the task, including:

- `BRAND_AND_FRONTEND_SPEC.md`
- `FRONTEND_ARCHITECTURE_SPEC.md`
- `LAUNCH_JOURNEYS_SPEC.md`
- `API_CONTRACT.md`
- `GUARDRAILS_RUNTIME_AND_SECURITY.md`

STOP if:

- Any requested UI change conflicts with this file or the listed authoritative MD files.
- A design requires funding-success claims, probability claims, or grant-win guarantees.
- A build requires backend/API behaviour not defined in `API_CONTRACT.md`.
- A frontend task introduces secrets, auth tokens in localStorage, or business logic that belongs to the backend.

No speculative components. No unused sections. No decorative UI that is not visible in the approved design direction.

---

## 1. Brand Positioning

NGOInfo is a practical funding support platform for NGOs.

The brand must feel:

- Trusted
- Clear
- Human
- Low-cost
- NGO-specific
- Practical rather than flashy
- AI-assisted, not AI-hyped

The design must communicate one core message:

> NGOInfo helps NGOs discover relevant funding opportunities and use GrantPilot AI to assess fit and draft stronger proposals.

Avoid language that implies NGOInfo guarantees funding, improves win probability, raises funds for NGOs, or acts as a donor intermediary.

---

## 2. Visual Identity

### 2.1 Logo

Use the NGOInfo logo in the header and footer.

Rules:

- Keep original colour.
- Do not recolour.
- Do not stretch.
- Do not crop.
- Maintain clear space around the logo.
- Header logo should be visually compact.
- Footer logo may be larger and white/light if placed on dark navy.

Recommended header logo size:

- Desktop width: 105–130px
- Mobile width: 95–115px

---

## 3. Colour System

### 3.1 Core Colours

Use these as implementation tokens.

```css
:root {
  --ngoinfo-navy: #1A1F71;
  --ngoinfo-navy-dark: #111653;
  --ngoinfo-navy-deep: #101828;
  --ngoinfo-blue: #2563EB;
  --ngoinfo-purple: #6D35FF;
  --ngoinfo-purple-dark: #4F2BD9;
  --ngoinfo-purple-light: #8B5CFF;
  --ngoinfo-bg: #F7F8FC;
  --ngoinfo-bg-soft: #F3F5FA;
  --ngoinfo-card: #FFFFFF;
  --ngoinfo-border: #E2E6F0;
  --ngoinfo-divider: #EEF1F7;
  --ngoinfo-text: #1F2937;
  --ngoinfo-text-muted: #64748B;
  --ngoinfo-success: #059669;
  --ngoinfo-warning: #D97706;
  --ngoinfo-error: #DC2626;
  --ngoinfo-footer: #101828;
}
```

### 3.2 Primary Usage

- Navy is the primary brand colour.
- Purple is used for high-emphasis CTA buttons, step numbers, tags, and key accents.
- Blue is used sparingly for links and small navigation affordances.
- Dark navy is used for final CTA bands and stats sections.
- Light grey backgrounds separate page sections.
- Cards are always white.

### 3.3 Colour Restrictions

Do not introduce:

- Bright neon colours
- Heavy multicolour gradients
- Red or orange as primary CTA colours
- Dark backgrounds outside footer, stats band, or final CTA band
- Random Tailwind colour choices not mapped to the tokens above

---

## 4. Typography

### 4.1 Font Family

Use one clean sans-serif family across the site.

Preferred:

```css
font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

Fallback allowed only if DM Sans is unavailable.

### 4.2 Type Scale

Desktop:

```css
--font-hero: 48px;
--line-hero: 56px;
--font-h1: 40px;
--line-h1: 48px;
--font-h2: 32px;
--line-h2: 40px;
--font-h3: 22px;
--line-h3: 30px;
--font-body: 16px;
--line-body: 24px;
--font-small: 14px;
--line-small: 20px;
--font-micro: 12px;
--line-micro: 16px;
```

Mobile:

```css
--font-hero-mobile: 34px;
--line-hero-mobile: 42px;
--font-h1-mobile: 32px;
--line-h1-mobile: 40px;
--font-h2-mobile: 26px;
--line-h2-mobile: 34px;
--font-body-mobile: 16px;
--line-body-mobile: 24px;
```

### 4.3 Heading Rules

- Hero headings must be bold, navy, and direct.
- Section headings must be centred on marketing pages unless the layout is a two-column feature block.
- Avoid long headings.
- Avoid generic AI language.

Example heading style:

```css
font-weight: 700;
color: var(--ngoinfo-navy);
letter-spacing: -0.02em;
```

---

## 5. Layout System

### 5.1 Page Width

Use a consistent max-width.

```css
--container-max: 1120px;
--container-narrow: 900px;
```

Rules:

- Main content max width: 1120px.
- Text-heavy sections max width: 900px.
- Cards must align to the same grid.
- Do not use full-width text blocks except dark CTA bands.

### 5.2 Spacing

Use an 8px spacing grid.

Allowed values:

```css
4px, 8px, 12px, 16px, 24px, 32px, 40px, 48px, 64px, 80px, 96px
```

Section padding:

- Desktop: 72–96px vertical
- Mobile: 48–64px vertical

Card padding:

- Desktop: 24–32px
- Mobile: 20–24px

### 5.3 Background Pattern

Approved section rhythm:

1. White header
2. Light grey hero
3. White trust strip
4. Light grey problem/value section
5. White product comparison section
6. Light grey process section
7. White feature cards
8. Light grey pricing
9. White FAQ/latest opportunities
10. Dark navy stats or final CTA
11. Dark footer

Do not place too many consecutive white sections.

---

## 6. Header

### 6.1 Desktop Header

Header must be simple and institutional.

Structure:

- Logo left
- Minimal nav centred/right
- Primary CTA button right

Recommended nav items:

- How It Works
- Funding Opportunities
- GrantPilot
- Pricing
- About
- Contact Us

Header rules:

- White background
- Thin bottom border optional
- Sticky header optional
- No heavy shadow
- CTA label: `Try GrantPilot Free`
- CTA style: navy filled button

### 6.2 Mobile Header

- Logo left
- Menu icon right
- CTA may be inside mobile menu
- Menu must not exceed one screen height
- Keep nav labels unchanged

---

## 7. Buttons and CTAs

### 7.1 Primary CTA

Use for main conversion actions.

```css
background: var(--ngoinfo-navy);
color: #FFFFFF;
border-radius: 8px;
padding: 14px 24px;
font-size: 15px;
font-weight: 700;
```

Hover:

```css
background: var(--ngoinfo-navy-dark);
```

Approved labels:

- Try GrantPilot Free
- Start Your Free Fit Scan
- Draft Proposal with GrantPilot AI

### 7.2 Purple CTA

Use for strong conversion emphasis inside process/pricing/final CTA sections.

```css
background: linear-gradient(135deg, #6D35FF 0%, #8B5CFF 100%);
color: #FFFFFF;
```

Approved labels:

- Start Your Free Fit Scan
- Start with Growth

### 7.3 Secondary CTA

Use for lower-intent actions.

```css
background: transparent;
color: var(--ngoinfo-navy);
border: 1px solid var(--ngoinfo-navy);
border-radius: 8px;
```

Approved labels:

- Browse Funding Opportunities
- View Details
- Learn More

### 7.4 CTA Rules

- One primary CTA per section.
- Do not use more than two CTA styles in one section.
- Do not use vague labels like `Submit`, `Explore`, or `Get Started` unless the destination is obvious.
- Button text must be sentence case or title case consistently within the section.

---

## 8. Cards

### 8.1 Standard Card

Use for pain points, tools, features, pricing, FAQs, and opportunity previews.

```css
background: #FFFFFF;
border: 1px solid var(--ngoinfo-border);
border-radius: 12px;
box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
padding: 24px;
```

### 8.2 Feature Card

Feature cards may use a slim purple left/top accent.

Rules:

- White background.
- Thin border.
- Small icon or accent allowed.
- Purple accent must be subtle.
- Do not use large illustrations unless supplied.

### 8.3 Pricing Card

Pricing cards must be clean and comparison-friendly.

Rules:

- Three columns on desktop.
- Single column on mobile.
- Highlight recommended plan with stronger shadow and navy/purple price pill.
- Price pill must be visually prominent.
- Feature lists use checkmarks.

Recommended plans:

- Free
- Growth
- Impact

Pricing visible in current design:

- Free: `$0`
- Growth: `$39 / Month`
- Impact: `$799 / Month`

If product pricing contract differs, STOP and ask whether pricing content or design screenshot is authoritative.

---

## 9. Icons

Use simple line icons only.

Approved icon style:

- 1.5–2px stroke
- Rounded corners
- Navy or purple
- Small contained icon blocks for cards

Do not use:

- 3D icons
- Emoji as product icons
- Cartoon illustrations
- Mixed icon libraries in the same section

---

## 10. Section Patterns

### 10.1 Hero Section

Hero must be direct and conversion-led.

Approved structure:

- Small eyebrow text
- Large navy headline
- Short explanatory paragraph
- Primary CTA
- Secondary CTA
- Right-side visual placeholder, product screenshot, or concise proof panel

Hero copy pattern:

```text
Stop wasting time on grants you were never eligible for.
```

Supporting copy must stay clear and avoid exaggerated claims.

### 10.2 Trust Strip

Use small badges/logos/tags to signal funder/discovery coverage.

Examples:

- USAID
- FCDO
- EU
- UNDP
- World Bank
- Ford Foundation

Rules:

- Light grey chips.
- No oversized logos unless permission/assets exist.
- Do not imply partnership unless verified.

### 10.3 Problem Section

Use a centred heading plus 3 cards.

Current approved pain themes:

- Hours lost on ineligible grants
- Consultants charge too much per proposal
- Generic AI tools do not speak donor language

Tone must be empathetic, not fear-based.

### 10.4 Two-Tool Section

Use two side-by-side cards:

1. `This Website` / funding discovery engine
2. `AI Workspace` / proposal drafting workspace

Each card should include:

- Pill label
- Short heading
- 2–3 sentence explanation
- Checkmark list
- CTA

### 10.5 Four-Step Process

Use four numbered steps.

Approved sequence:

1. Set up your NGO profile
2. Pick a funding opportunity
3. Run a Fit Scan
4. Generate your proposal

Step numbers must use purple.

### 10.6 Feature Grid

Use six cards maximum.

Approved feature themes:

- Fit Scan
- Structured Proposals
- Sector-Specific AI
- Honest Risk Flags
- DOCX Export
- Works With Any Donor

### 10.7 FAQ Section

FAQ style:

- White background
- Thin separators
- Question in navy/bold
- Answer in muted text
- No accordion required unless page gets long

Approved FAQs:

- Is this just ChatGPT with a wrapper?
- Will GrantPilot write my entire proposal?
- What if the Fit Scan says “Not Recommended”?

### 10.8 Stats Band

Use dark navy full-width section.

Approved stat format:

- Large number
- Short label
- 3 columns desktop
- Single column mobile

Current sample stats:

- `34+` funding opportunities listed
- `8+` donor organisations covered
- `1` continent represented

### 10.9 Latest Opportunities

Opportunity cards should show:

- Opportunity title
- Donor
- Deadline
- `View Details →`

Rules:

- 3 cards desktop.
- Single column mobile.
- Keep cards compact.

### 10.10 Final CTA Band

Use dark navy or purple/navy gradient.

Approved heading:

```text
Your next proposal is 5 minutes away.
```

Use two CTAs:

- Try GrantPilot Free
- Browse Funding Opportunities

---

## 11. Footer

Footer must be dark and practical.

Structure:

- Logo and short description left
- Platform links centre
- Contact details right
- Bottom legal bar

Approved footer sections:

Platform:

- This Website
- Funding Opportunities
- GrantPilot
- Pricing
- About
- Contact Us

Contact:

- Registered office / location
- Support email

Legal:

- Terms & Conditions
- Privacy Policy

Footer colours:

```css
background: var(--ngoinfo-footer);
color: #FFFFFF;
muted text: #CBD5E1;
links: #E5E7EB;
```

---

## 12. Content Tone

### 12.1 Voice

Use a direct, founder-led, practical tone.

Good:

- Clear
- Specific
- Calm
- Helpful
- Honest about limits

Avoid:

- Hype
- Fear-based selling
- Corporate jargon
- Generic AI claims
- Overpromising

### 12.2 Banned Claims

Do not use:

- Win more grants
- Increase your chances
- Guaranteed funding
- Success probability
- We raise funds for NGOs
- Donor access guaranteed
- AI replaces grant writers
- Fully automated submission
- Apply with confidence if that implies outcome confidence

### 12.3 Approved Phrases

Use:

- Check whether an opportunity is worth your time
- Understand fit before you apply
- Draft a structured proposal
- Review risks before drafting
- Export a DOCX draft
- Funding discovery and proposal drafting
- Built for NGO grant workflows
- AI-assisted, not auto-submitted

---

## 13. Accessibility

Minimum requirements:

- Body text minimum 14px.
- Buttons must have accessible labels.
- Colour contrast must meet WCAG AA.
- Do not communicate status by colour alone.
- All links must be keyboard accessible.
- Focus states must be visible.
- Images must have meaningful alt text or empty alt if decorative.

---

## 14. Responsive Rules

### Desktop

- Use max-width containers.
- Hero can use 2 columns.
- Cards can use 2 or 3 columns.
- Pricing uses 3 columns.

### Tablet

- 2-column grids where readable.
- Avoid cramped pricing cards.

### Mobile

- Single-column layout.
- CTAs stack vertically.
- Hero visual moves below copy or is hidden if low-value.
- Pricing cards stack Free → Growth → Impact.
- Footer stacks vertically.

---

## 15. WordPress / Gutenberg / Spectra Build Rules

When implementing in WordPress:

- Prefer reusable block patterns.
- Keep CSS scoped to the page/template where possible.
- Avoid heavy page-builder effects.
- Avoid layout-breaking absolute positioning.
- Use semantic headings in correct order.
- Do not hardcode dynamic funding opportunities if a WordPress query/block can render them.
- Keep CTA links configurable.

Recommended CSS class prefix:

```css
.ngi-
```

Examples:

```css
.ngi-hero
.ngi-section
.ngi-card
.ngi-pricing-card
.ngi-cta-band
.ngi-footer
```

---

## 16. GrantPilot Handoff Rules

Marketing pages may link to GrantPilot using:

```text
https://grantpilot.ngoinfo.org/start?opportunity_id={uuid}&source=wp
```

Rules:

- Preserve opportunity context.
- Do not claim WordPress performs Fit Scan or proposal generation.
- GrantPilot workspace owns auth, profile, Fit Scan, proposal generation, export, billing, and quota.
- NGOInfo.org remains discovery and marketing layer.

---

## 17. Implementation Checklist for Cursor

Before completing any frontend task, verify:

- Logo is correct and not distorted.
- Colours use the token system.
- Font is DM Sans or approved fallback.
- Header matches the approved structure.
- CTA labels are specific and action-oriented.
- Cards use consistent radius, border, and shadow.
- Section spacing follows the approved rhythm.
- Mobile layout does not break.
- No banned claims appear in copy.
- No new product/API behaviour is invented.
- No secrets are added to frontend code.

---

## 18. Definition of Done

A page or component is complete only when:

- It visually matches the approved NGOInfo design direction.
- It uses the tokens in this file.
- It respects all content and compliance rules.
- It is responsive across desktop, tablet, and mobile.
- It has no console errors.
- It does not introduce contract drift.
- It can be reused safely in future NGOInfo builds.
