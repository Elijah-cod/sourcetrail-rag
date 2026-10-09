# SourceTrail design

SourceTrail answers questions from your documents and shows exactly which passage supports each
claim. The interface is a calm product UI whose job is **ask, inspect the evidence, verify**.
Everything visual should serve that loop; decoration that doesn't is removed.

## Principles

1. **Evidence first.** Citations, passages and "not found in any source" warnings are the most
   important things on screen. They get colour; chrome doesn't.
2. **Say it in words.** Status is written out ("Needs attention: 3 questions…", "Writing an
   answer from 6 passages…"), never carried by colour alone.
3. **Quiet by default.** One accent hue, flat surfaces, few borders. Prefer a tint or weight
   change over adding another card, stripe or gradient.
4. **Works for everyone.** Keyboard, screen reader, phone and reduced-motion users get the same
   product (see Accessibility below).

## Colour

Tokens live in `frontend/src/app/globals.css` (`@theme`) and are used as Tailwind classes.
Components use **role names, never raw palette colours**, so restyling or adding a dark theme
means changing values in one place.

| Token | Use | Currently |
|---|---|---|
| `surface` | page background | `#faf8ff` |
| `raised` | cards, panels, inputs, popovers | white |
| `ink-*` | text, borders, neutral fills | slate |
| `brand-*` | the accent: primary actions, links, selection, active nav | indigo |
| `success-*` | grounded answers, passing checks | emerald |
| `warning-*` | needs checking: weak matches, unsourced figures, benchmark issues | amber |
| `danger-*` | errors, failed uploads, delete | rose |
| `highlight` | the sentence in a passage that supports the clicked claim | yellow-200 |
| `primary` | keyboard focus ring | `brand-600` |

Text steps: `ink-900` headings and answer text, `ink-700`/`ink-800` body, `ink-600` secondary,
`ink-500` the lightest allowed for text or icon-only buttons (4.8:1 on white). `ink-400` is for
list markers and decoration only.

**Categorical palettes are the exception.** Citation numbers (`lib/citations.ts`) and file-type
icons (`components/FileTypeIcon.tsx`) cycle through raw hues (indigo, violet, amber, teal, rose,
sky…) so items are easy to tell apart. A red PDF icon doesn't mean "danger", so these don't use
role tokens.

## Type

- Fonts: Plus Jakarta Sans (UI), Hanken Grotesk (`font-heading`), JetBrains Mono (`font-mono`:
  ids, timings, citation numbers).
- Answer text 14.5px, relaxed leading. Body and controls 13–14px.
- Supporting text (metadata, hints, labels): 13px. **Nothing below 12px.**
- Headings: page `text-xl`, section 15px bold.

## Layout and touch targets

- Breakpoints: phone first; `sm` 640, `md` 768, `lg` 1024 (side panels become columns).
- Icon buttons are 40 × 40; the send button is 44 × 44; text buttons and fields are at least
  40px tall.
- Inline citation chips and pills keep their compact look and use the `tap-target` utility
  (an invisible 44 × 44 hit area) so they don't reflow text.
- Dense tables become stacked cards below `sm` (see the Benchmarks question list); otherwise
  show a "swipe sideways" hint.

## Components

- **Cards:** `rounded-xl`/`2xl`, `border-ink-200`, `bg-raised`. Don't nest a card in a card;
  inside a card use spacing, a divider or a single line of figures instead.
- **Pills:** status pills (`Grounded in 2 sources`, `Strong match`) use the role colours.
  Don't add pills for decoration.
- **Active state:** tint + weight (+ dot for nav). No side stripes.
- **Side panels** (navigation, sources): columns on `lg+`; below that, modal drawers via
  `useModalDrawer` (focus moves in, Tab is trapped, Escape closes, focus returns).
- **Popovers:** `role="dialog"` with a title; focus the first field on open; Escape returns
  focus to the trigger.

## Motion

Short and functional: drawer slides (200ms), the passage flash when a citation is clicked, the
loading dots. All of it turns off under `prefers-reduced-motion` (spinners keep turning, as the
only sign an upload is running). JavaScript scrolling uses `scrollBehavior()` from
`lib/motion.ts`.

## Accessibility checklist

- Every control has an accessible name that contains its visible text (WCAG 2.5.3).
- Keyboard focus is always visible (`:focus-visible` outline in `primary`).
- Text contrast at least 4.5:1, control and icon contrast at least 3:1.
- Live status (`role="status"` / `aria-live`) for loading stages and upload progress.
- Test at 375 × 812 and 1440 × 900: no page-level horizontal scroll.

## Avoid

Gradients on icons or avatars, custom scrollbars, coloured side stripes, rows of pastel metric
cards, new hues outside the tokens, and text smaller than 12px.
