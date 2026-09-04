# DESIGN.md — "EDGAR Register"

This document describes the visual design system of the Stocks frontend as it actually exists in code today. It is derived from the shipped source (`frontend/app/globals.css`, `layout.tsx`, and the components listed below), not from a plan or intention. If something here stops matching the code, the code wins — update this file.

The system is called **EDGAR Register**: a light, federal-filing-system, utilitarian aesthetic (think SEC EDGAR, a register of public filings) — chosen deliberately to move away from a generic "AI dashboard" look (near-black background, saturated purple accent, glow/blur decoration).

## Color tokens

All tokens are defined once in `frontend/app/globals.css` under `:root`, then re-exposed as Tailwind theme colors via `@theme inline` (so `bg-accent`, `text-muted-foreground`, `border-border-strong`, etc. are all available as Tailwind utility classes). There is no dark-mode block — `layout.tsx` hardcodes `data-theme="light"` on `<html>`.

| Token | Hex | Semantic use |
|---|---|---|
| `--color-primary` | `#16181d` | Near-black; not directly used as a Tailwind color in the pages inspected, but backs `--color-foreground`. |
| `--color-on-primary` | `#ffffff` | Text/icon color for content on top of `--color-primary`. |
| `--color-secondary` | `#eef0f2` | Secondary light surface token. |
| `--color-on-secondary` | `#16181d` | Text on `--color-secondary`. |
| `--color-accent` | `#1a4480` | The **Insiders** category color (federal blue). Used for: primary buttons (Search), links/hover-underline on actor names and tickers, active nav underline (Header, "Trade Tracker" tab), active category-tab underline + text for the Insiders tab, focus rings (`focus-visible:ring-accent/70`), the actor-filter chip text, and `--color-ring`. |
| `--color-on-accent` | `#ffffff` | Text on accent-filled surfaces (e.g. the Search button). |
| `--color-background` | `#f4f5f7` | Page/body background — a slightly gray-tinted off-white, not pure white. |
| `--color-foreground` | `#16181d` | Default body text color. |
| `--color-card` | `#fbfbfa` | Card/panel/table/input background — a hair lighter/warmer than the page background, giving cards subtle separation without a shadow. |
| `--color-card-foreground` | `#16181d` | Primary text inside cards (row titles, cell values). |
| `--color-muted` | `#e8eaed` | Muted fill: hover backgrounds (`hover:bg-muted`), skeleton-loading blocks, expanded-row detail-panel background, progress-bar track background, empty-state icon tile background. |
| `--color-muted-foreground` | `#4b5563` | Secondary/label text: column headers in expanded rows, helper text, dates, placeholder text, inactive tab text. |
| `--color-border` | `#d6d9df` | Low-contrast hairline divider. Used only for **non-interactive** boundaries: row dividers, card outlines, header bottom border, tab-strip bottom border — where the fill-color change alongside it also signals the boundary, not the sole cue. |
| `--color-border-strong` | `#818a9b` | Higher-contrast border reserved for **interactive control boundaries**: text inputs, date inputs, selects, buttons ("Refresh now", "Export CSV", "Load more", "View original filing"), the logo mark's icon frame. |
| `--color-destructive` | `#b91c1c` | Error/negative semantic color: error banners, "Sell"/"Disposed" transaction badges, "[Exited]" position-change badge, sell-side of the buy/sell ratio bar. |
| `--color-on-destructive` | `#ffffff` | Text on a filled destructive surface (not currently used filled anywhere inspected — destructive surfaces are tinted `/10`, not solid-filled). |
| `--color-positive` | `#166534` | The **Congress** category color, and the general positive/buy semantic color. Used for: "Buy"/"Acquired" badges, "[New]" position-change badge, buy-side of the buy/sell ratio bar, "Verified" source label, active Congress tab underline+text, Congress icon tile on the ticker page, the homepage "live" pulse dot and "[Live]" badge. |
| `--color-on-positive` | `#ffffff` | Text on a filled positive surface. |
| `--color-warning` | `#92400e` | Warning semantic color: "Unverified" source label, scrape-error indicator text, export-truncation notice. |
| `--color-on-warning` | `#ffffff` | Text on a filled warning surface. |
| `--color-info` | `#9a3412` | The **Institutions** category color — a muted federal-document-stamp brick red-brown, deliberately distinct from both `--color-accent` (Insiders) and `--color-positive` (Congress). Used for: active Institutions tab underline+text, Institutions icon tile, "All changes/New/Exited/Changed" filter-tab active state on the Position Changes view. |
| `--color-on-info` | `#ffffff` | Text on a filled info surface. |
| `--color-ring` | `#1a4480` | Focus-ring color (same value as `--color-accent`); actual focus rings in components are hand-written as `focus-visible:ring-accent/70` or `/40` rather than referencing this token directly. |

**The three data-category colors, at a glance:**

| Category | Color token | Hex |
|---|---|---|
| Corporate Insiders | `--color-accent` | `#1a4480` (federal blue) |
| Institutions (13F) | `--color-info` | `#9a3412` (brick red-brown) |
| Congress | `--color-positive` | `#166534` (green) |

Each category's color is applied consistently across three surfaces wherever that category appears: the icon tile/frame, the active tab underline + tab text, and (for Institutions/Congress on the ticker page) the section icon color. This is the load-bearing pattern for category identity — there is no separate "category badge" component; the color itself is the signifier.

## Typography

Loaded in `frontend/app/layout.tsx` via `next/font/google`:

- **Public Sans** (`Public_Sans`, weights 400/500/600/700) → CSS variable `--font-public-sans` → Tailwind `--font-sans`. This is the default UI/body font (headings, buttons, labels, paragraph copy, nav). Applied at the `body` level in `globals.css`.
- **Fira Code** (`Fira_Code`, weights 400/500/600/700) → CSS variable `--font-fira-code` → Tailwind `--font-mono`. Used everywhere data or machine-readable values are shown: table cell values (`renderCell`), tickers, CUSIPs, dollar amounts (`formatMeta`), dates inside rows, badges/tags (`[Acquired]`, `[+12%]`, `[House]`), the "Verified · <source>" status lines, actor-filter chips, and sort-order selects showing column keys.

Both fonts load as variable-weight Google Fonts with `antialiased` applied on `<html>`. There is no separate display/serif font — headings use Public Sans at larger sizes/weight (`text-2xl font-semibold tracking-tight` etc.), not a distinct typeface.

**Rule of thumb:** prose/labels/interactive text → sans (Public Sans, the default). Anything that is a literal data value, code, identifier, or tag → mono (Fira Code, applied explicitly via `font-mono`).

## Component patterns

**Badges/tags** (`frontend/app/lib/tradeFormat.tsx`, `badge()`): plain bracketed monospace text — `[Acquired]`, `[Disposed]`, `[New]`, `[+12%]` — colored by semantic tone (`text-positive` / `text-destructive` / `text-muted-foreground`), `font-mono text-xs font-semibold uppercase tracking-wide`. **No filled background, no pill shape, no border** — the brackets themselves do the work a chip's shape would otherwise do. This pattern repeats independently in `PositionChanges.tsx`'s `changeBadge()`.

**Category tabs** (`Header.tsx`, `trade-tracker/page.tsx`, `PositionChanges.tsx`): plain text buttons with a 2px bottom border (`border-b-2`) that is `border-transparent` when inactive and the category color when active (`border-accent text-accent`, `border-info text-info`, `border-positive text-positive`). No background fill, no rounded pill treatment — this is an underlined-text-tab pattern, consistently applied for primary nav, the three data-category tabs, and the secondary Institutions holdings/changes sub-tabs, and the position-change type filter.

**Cards/panels**: flat rectangles — `border border-border bg-card`, **zero border-radius everywhere** (no `rounded-*` class appears anywhere in the app except one exception below). This applies to the table container, stat tiles, the homepage product card, empty-state icon tile, and expanded-row detail panels. Hover/interaction state is communicated by border-color change (`hover:border-accent`) or background tint (`hover:bg-muted`), never by elevation/shadow — no `shadow-*` or `blur-*` class appears anywhere in the codebase.

- The one `rounded-full` in the entire app is the small pulsing "live" status dot on the homepage (`animate-pulse-dot`) — a conventional round status-indicator dot, not a structural/chrome element, and it's the sole exception to the flat-rectangle rule.
- The hero SVG illustration on the homepage uses `rx="1.5"` on tiny candlestick bars purely as chart illustration detail, not UI chrome.

**Inputs/buttons**: `border border-border-strong bg-card`, flat, `focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70` (or `/40` on text inputs) for focus state. Primary action (Search) is solid `bg-accent text-on-accent`; secondary actions (Refresh, Export, Load more, View original filing) are outlined (`border-border-strong`) with a muted hover fill and no fill at rest.

**Row expand/collapse**: chevron rotates 180° on open (`transition-transform`), row background tints `bg-muted/40` when open, detail panel below uses a `<dl>` grid of label/value pairs with mono values.

**Status/verification language**: "Verified" (positive/green) vs "Unverified" (warning/amber) is a recurring, explicit primitive — shown both at the table-summary level and per-row, since some categories (Congress) mix sources of differing reliability.

## What NOT to do (explicit anti-patterns)

Derived from what is consistently absent from the shipped code:

- **No rounded corners on structural elements.** Cards, buttons, inputs, tables, tabs, badges are all hard-cornered. The only rounded shape in the app is a small circular status dot.
- **No decorative blur, glow, or shadow.** Zero `shadow-*`, `blur-*`, or `backdrop-*` classes exist anywhere in `frontend/app`. Separation between surfaces comes from a 1px border and a small background-value shift (`--color-card` vs `--color-background`), never elevation.
- **No filled, pill-shaped badges.** Status/category tags are bracketed monospace text in a semantic color, not colored chips with rounded backgrounds.
- **No near-black background / no saturated purple / no neon-on-dark.** The whole palette is light (`--color-background: #f4f5f7`, `--color-card: #fbfbfa`); the closest thing to a "brand" color is the muted federal blue `--color-accent` (#1a4480) — not a saturated purple, and there is no dark theme defined at all (`data-theme="light"` is hardcoded).
- **No filled category pills for tabs.** Category identity is carried by an underline + text color on a plain button, not a colored background pill.
- **Motion is restrained and respects `prefers-reduced-motion`.** The two decorative animations (`animate-fade-up` row/section entrance, `animate-pulse-dot` live indicator) are explicitly zeroed out under `prefers-reduced-motion: reduce` in `globals.css` — but scoped narrowly to those two classes rather than a blanket `*` override, so functional transitions (hover, focus rings, the expand-caret rotation) still communicate state changes for users who need reduced motion.

## Accessibility notes

- **`--color-border` vs `--color-border-strong` is a deliberate, documented contrast split** (see the comment block at the top of `globals.css`): `--color-border` (#d6d9df) is a low-contrast hairline used only for non-interactive dividers (row separators, card outlines) where an adjacent fill-color change also signals the boundary. `--color-border-strong` (#818a9b) is reserved for interactive control boundaries — inputs, selects, buttons — and is verified to clear **3:1** contrast against the card background, since WCAG requires that minimum for UI-component boundaries that are the *sole* visual cue for "this is a control." Do not use plain `--color-border` as the only outline on a new interactive element.
- **Text pairings are verified to clear 4.5:1** (per the same comment block) for standard body/label text against their backgrounds.
- **Text-opacity utilities need contrast-checking before use, not assumed safe.** This project previously shipped `/50` and `/70` opacity variants on muted text that failed contrast; the values actually shipped today use **`/85`** as the floor for opacity-reduced muted text (`text-muted-foreground/85`, used for empty-cell placeholders `—` and secondary disclaimers) — grep confirms `/85` is the only opacity suffix applied to `muted-foreground` text anywhere in the app. Treat `/85` as the practical safe floor for muted-foreground-on-card text opacity; do not reintroduce `/50` or `/70` on text without re-checking contrast. (Non-text uses of low opacity — e.g. `bg-warning/10`, `border-destructive/40` for banner fills/outlines, or the `/28` gradient stop in the decorative hero SVG — are a different case and aren't subject to the same text-contrast rule.)
