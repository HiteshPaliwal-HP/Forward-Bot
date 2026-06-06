---
name: Forward Bot
description: Operator dashboard for a self-hosted Telegram forwarding worker. shadcn/ui on React + Tailwind; this DESIGN.md specifies the brand-layer delta only.
status: final
updated: 2026-05-31
sources:
  - ../../prds/prd-forward-bot-2026-05-31/prd.md
  - ../../prds/prd-forward-bot-2026-05-31/addendum.md
colors:
  # Brand overrides on top of shadcn defaults. Unlisted tokens (popover, card,
  # input, ring, etc.) inherit from shadcn's stone/zinc palette.
  # ---- LIGHT ----
  background: '#FAFAF9'
  background-muted: '#F4F4F2'
  border: '#E7E5E0'
  foreground: '#1C1917'
  foreground-muted: '#78716C'
  accent: '#16A34A'
  accent-hover: '#15803D'
  accent-foreground: '#FFFFFF'
  state-success: '#16A34A'
  state-success-bg: '#F0FDF4'
  state-success-border: '#BBF7D0'
  state-success-foreground: '#15803D'
  state-warning: '#D97706'
  state-warning-bg: '#FEF3C7'
  state-warning-border: '#FDE68A'
  state-warning-foreground: '#92400E'
  state-error: '#DC2626'
  state-error-bg: '#FEF2F2'
  state-error-border: '#FECACA'
  state-degraded-bg: '#FEF2F2'
  state-degraded-border: '#FCA5A5'
  state-degraded-foreground: '#991B1B'
  state-muted: '#A8A29E'
  state-muted-bg: '#F4F4F2'
  # ---- DARK ----
  background-dark: '#14130F'
  background-muted-dark: '#1C1B16'
  border-dark: '#2A2823'
  foreground-dark: '#E7E5E0'
  foreground-muted-dark: '#A8A29E'
  accent-dark: '#22C55E'
  accent-hover-dark: '#16A34A'
  accent-foreground-dark: '#052E16'
  state-success-dark: '#22C55E'
  state-success-bg-dark: 'rgba(34,197,94,0.12)'
  state-success-border-dark: 'rgba(34,197,94,0.35)'
  state-success-foreground-dark: '#4ADE80'
  state-warning-dark: '#F59E0B'
  state-warning-bg-dark: 'rgba(245,158,11,0.14)'
  state-warning-border-dark: 'rgba(245,158,11,0.45)'
  state-warning-foreground-dark: '#FCD34D'
  state-error-dark: '#EF4444'
  state-error-bg-dark: 'rgba(239,68,68,0.12)'
  state-error-border-dark: 'rgba(239,68,68,0.35)'
  state-degraded-bg-dark: 'rgba(239,68,68,0.14)'
  state-degraded-border-dark: 'rgba(239,68,68,0.45)'
  state-degraded-foreground-dark: '#FCA5A5'
  state-muted-dark: '#78716C'
  state-muted-bg-dark: '#1C1B16'
typography:
  # All roles inherit shadcn's default sans (Geist or system-ui) at shadcn's
  # default ramp. Only `mono` is named because log rows and correlation IDs
  # use it heavily — shadcn names it but the operator product leans on it.
  mono:
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'
    fontSize: 12px
    lineHeight: '1.5'
rounded:
  # shadcn defaults — --radius: 0.5rem (8px). Inherited as-is.
  sm: 4px
  md: 6px
  lg: 8px
  full: 9999px
spacing:
  # shadcn / Tailwind 4-based scale inherited. No overrides.
components:
  button-primary:
    background: '{colors.accent}'
    foreground: '{colors.accent-foreground}'
    hover: '{colors.accent-hover}'
    radius: '{rounded.md}'
  toggle-on:
    background: '{colors.accent}'
    foreground: '{colors.accent-foreground}'
    radius: '{rounded.full}'
  pill-success:
    background: '{colors.state-success-bg}'
    border: '{colors.state-success-border}'
    foreground: '{colors.state-success-foreground}'
    radius: '{rounded.full}'
  banner-degraded:
    background: '{colors.state-degraded-bg}'
    border: '{colors.state-degraded-border}'
    foreground: '{colors.state-degraded-foreground}'
    radius: '0'
  log-row-forwarded:
    accent-color: '{colors.state-success}'
    icon: 'lucide:arrow-up-right'
  log-row-filter-blocked:
    accent-color: '{colors.state-muted}'
    icon: 'lucide:circle-slash'
  log-row-telegram-rejected:
    accent-color: '{colors.state-error}'
    icon: 'lucide:alert-triangle'
  log-row-destination-unreachable:
    accent-color: '{colors.state-error}'
    icon: 'lucide:ban'
  filter-icon-active:
    color: '{colors.accent}'
    opacity: '1.0'
  filter-icon-inactive:
    color: '{colors.foreground-muted}'
    opacity: '0.4'
  log-row-flood-wait:
    accent-color: '{colors.state-warning}'
    icon: 'lucide:clock'
  log-row-edit-propagated:
    accent-color: '{colors.state-success}'
    icon: 'lucide:pencil'
  log-row-delete-propagated:
    accent-color: '{colors.state-success}'
    icon: 'lucide:trash-2'
  log-row-reply-orphaned:
    accent-color: '{colors.state-warning}'
    icon: 'lucide:corner-down-right'
  pill-cache-stale:
    background: '{colors.state-warning-bg}'
    border: '{colors.state-warning-border}'
    foreground: '{colors.state-warning-foreground}'
    radius: '{rounded.full}'
---

# Forward Bot — DESIGN.md

> Visual identity spine. Distilled at Finalize from `.decision-log.md`, `.working/`, and the PRD addendum §9.3. Authored per the Google Labs DESIGN.md spec. **This spine wins on conflict with any mock, import, or downstream interpretation.**

## Brand & Style

Forward Bot is a self-hosted Telegram forwarding worker with an operator dashboard. The product is *infrastructure that happens to have a UI* — a background worker plus the surfaces you need to configure, observe, and verify it. The persona is a single operator running one instance for personal use; the register is operator-tool, not consumer app.

The visual posture: **pragmatic, not glossy.** Warm-stone neutrals so long config sessions don't fatigue, a single signal-green accent that means *the pipeline is alive*, terse type, dense-but-comfortable spacing. Brand discipline is "shadcn/ui defaults are correct" — Forward Bot inherits the shadcn surface wholesale and overrides only what the brand layer demands. Both light and dark are first-class (system-follow with manual toggle in Settings); the dark surface is where the operator will spend most evenings.

The product earns trust by *proving the pipeline runs* — Logs is not a diagnostic afterthought, it is the verification surface. The visual language must make a forwarded event read unmistakably differently from a blocked one, because watching that distinction change in real time is how the operator confirms a fix landed.

## Colors

The palette is warm-stone neutrals plus Forwarding Green plus three state colors. Every other token inherits from shadcn.

- **Background / surface (`#FAFAF9` light / `#14130F` dark)** is warm stone, not cold zinc. Long config sessions on this surface stay comfortable; the warmth keeps the chrome from feeling clinical. Border and muted backgrounds (`#E7E5E0` / `#F4F4F2` light, `#2A2823` / `#1C1B16` dark) form a low-contrast structural grid — chrome should recede.
- **Forwarding Green — accent (`#16A34A` light / `#22C55E` dark)** is the brand color and the "active pipeline" signal. Used on: primary buttons (`{components.button-primary}`), toggle-ON state (`{components.toggle-on}`), active filter icons (`{components.filter-icon-active}`), active sidebar nav, link underlines. Hover/active is `accent-hover` (a half-step darker).
- **State Success (`#16A34A` light / `#22C55E` dark)** — same hue family as accent but expressed differently. Success **never** appears as a solid fill on a CTA; it appears as a **tinted pill** (`{colors.state-success-bg}` background with `{colors.state-success-foreground}` text and `{colors.state-success-border}` border) or as the **left-border accent color on a log row**. This separation is load-bearing — see Do's-and-Don'ts.
- **State Warning (`#D97706` light / `#F59E0B` dark)** — reserved for warnings (cache-refresh pending, validation soft warnings). Not used on any primary surface.
- **State Error (`#DC2626` light / `#EF4444` dark)** — destructive confirmations, validation errors, `telegram_rejected` log rows, `destination_unreachable` log rows. Distinguished from `state-degraded` by usage scope: error = per-row / per-field; degraded = global system condition.
- **State Degraded (light `#FEF2F2` bg / `#991B1B` text; dark `rgba(239,68,68,0.14)` bg / `#FCA5A5` text)** — exclusively the global banner shown when Telegram is disconnected. A distinct red tone from `state-error` so the operator learns to read the banner as "the whole system is degraded" rather than "one thing failed."
- **State Muted (`#A8A29E` light / `#78716C` dark)** — filter-blocked log rows (`outside_time_window`, `sampled_out`, `blocked_keyword`, `media_type_filtered`). Muted means *not an error, just suppressed*.

All foreground/background pairs verified for WCAG AA contrast in both modes. The light/dark token pairs share the same semantic role; consumers should select via the active theme.

Visual reference: [mockups/color-themes.html](mockups/color-themes.html) shows the chosen variation (Forwarding Green on warm stone, variation 2) alongside the rejected alternatives — kept for audit trail.

## Typography

Inherits shadcn's default sans ramp (Geist Sans or system-ui) at shadcn's default sizes and weights. No display face — Forward Bot is not editorial; headings stay in the same family as body, weight-and-size carry hierarchy.

**Monospace** (`{typography.mono}`) is named because the operator surface leans on it more than a typical SaaS dashboard: log row payload previews, correlation IDs, Telegram numeric IDs, env-var values in Settings, and timestamps in the `+2m` short format. The mono face inherits the system's default (`ui-monospace, SFMono-Regular, Menlo, Consolas`).

No all-caps labels except shadcn's existing micro-label pattern (e.g., section dividers in Settings). No letter-spacing overrides.

## Layout & Spacing

shadcn / Tailwind 4-based spacing scale inherited as-is (4, 8, 12, 16, 20, 24, 32, 40, 48, 64). No overrides.

Desktop-first web. Primary layout is a **persistent left sidebar** (5 nav items: Dashboard, Forwards, Sources, Logs, Settings) plus a content pane with `max-w-6xl` for list/detail surfaces and full-width for Logs (the log stream wants horizontal room).

A **global top bar** spans the full width, holding breadcrumbs (left) and the Telegram connection status indicator (right). When degraded, a `{components.banner-degraded}` strip slides in immediately below the top bar, full-width, non-dismissible until the underlying condition clears.

Mobile responsive is **out of scope** per PRD §9.5 beyond "doesn't break at narrow widths." The sidebar collapses to a sheet below `md` (768px) but layouts are not re-composed for phones.

## Elevation & Depth

Inherited from shadcn — subtle shadow on raised surfaces (Popover, Dialog, DropdownMenu, Toast), no elevation used as hierarchy. Forward Bot adds nothing. Hierarchy comes from tone, position, and the warm-stone surface gradient (`background` < `background-muted` < `card` is shadcn's default), not from shadows.

The one deliberate elevation moment: the **first-run wizard modal** uses shadcn's `Dialog` elevation as-is. Toasts use shadcn's default `Toast` shadow; progress-bar toasts (bulk operations) do not get extra elevation despite their importance — the running counter and the progress bar do the work.

## Shapes

shadcn defaults: `--radius: 0.5rem` (8px) for cards and dialogs, 6px for buttons and inputs, 4px for small affordances. Pill shapes (`{rounded.full}`) for status pills (`{components.pill-success}`) and toggles (`{components.toggle-on}`).

The **global degraded banner** is the one exception — `radius: 0`. It spans edge to edge and reads as a system-level interruption, not a card. Sharp corners signal "this is the chrome telling you something."

## Components

Forward Bot uses the following shadcn components as-is, unchanged: `Button` (non-primary variants), `Card`, `Dialog`, `Sheet`, `Popover`, `DropdownMenu`, `Toast`, `Tabs`, `Avatar`, `Separator`, `Input`, `Textarea`, `Checkbox`, `RadioGroup`, `Select`, `Tooltip`, `Skeleton`, `Command`. The contract: don't customize these.

Brand-layer components (visual specs; behavior lives in EXPERIENCE.md):

- **Button — primary variant (`{components.button-primary}`)** — `accent` fill, `accent-foreground` text, `accent-hover` on hover, `{rounded.md}` corner. Used for "Save", "+ New Forward", "+ New Source", "Reconnect". Secondary, outline, ghost, destructive variants inherit shadcn defaults.
- **Toggle — ON state (`{components.toggle-on}`)** — `accent` track when active. shadcn's `Switch` component, brand-color override on `data-state=checked` only.
- **Status pill — success (`{components.pill-success}`)** — tinted background, distinct from accent solid. Used for "Telegram connected", "Rule active", "Source resolved". The visual difference between this and the primary button is the whole point: solid green = action; tinted green = state.
- **Banner — degraded (`{components.banner-degraded}`)** — full-width, edge-to-edge, `radius: 0`, distinct `state-degraded` red. Holds the message and a `[Reconnect]` button. Persists until condition clears; cannot be dismissed.
- **Log row** — left-edge accent stripe (4px wide) + lucide icon + bold event label + mono payload preview + timestamp on the right.
  - `forwarded` → `{components.log-row-forwarded}` (success green stripe, `arrow-up-right` icon).
  - `outside_time_window` / `sampled_out` / `blocked_keyword` / `media_type_filtered` → `{components.log-row-filter-blocked}` (muted stripe, `circle-slash` icon, label "Filter-blocked: {reason}").
  - `telegram_rejected` → `{components.log-row-telegram-rejected}` (error stripe, `alert-triangle` icon).
  - `destination_unreachable` → `{components.log-row-destination-unreachable}` (error stripe, `ban` icon — distinct icon from `telegram_rejected` even though both are red).
- **Filter icon row (S2)** — tiny lucide icons per filter type on each Forwards List row: `clock` (time-window), `shuffle` (sampling), `image` (media-type), `key` (keyword block/allow). Active = `{components.filter-icon-active}` (accent tint, full opacity). Inactive = `{components.filter-icon-inactive}` (40% opacity, muted color). Hover surfaces a tooltip with the configured value.
- **Collapsible panel header (S3)** — shadcn `Accordion` with a summary string baked into the trigger: "Filters — Block: 14 keywords, Time: off, Sampling: off, Media: all". The summary is rendered in `foreground-muted`; the panel name in `foreground`. The summary is load-bearing — see EXPERIENCE.md → Component Patterns.
- **Activation banner (S3, post-save)** — shadcn `Alert` variant, `state-warning` tint, sits at the top of the edit surface for any rule with `is_active=false`. Persists until first activation. Holds the message and a primary "Activate" button.
- **File picker (S3 media replacement)** — shadcn `Combobox` listing existing files in `MEDIA_REPLACEMENT_BASE_DIR`. Pick-only; the dashboard never writes to the directory. Operator places files via SFTP / `docker cp` / bind-mount.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Treat `{colors.accent}` and `{colors.state-success}` as **two separate roles** — accent is action (solid CTA, toggle-ON, primary nav active); state-success is *state* (tinted pill, log-row left-stripe). Same hue, different expression. | Use the accent solid fill for a status pill, or the success-tinted pill for a CTA. Collapsing the two undoes the climax beat in the operator's verification journey. |
| Inherit shadcn defaults wholesale for anything not explicitly in this DESIGN.md. | Re-document a token, component, or pattern just to "have it written down" — if it's the shadcn default, leave it. |
| Pair every state color with an **icon and a label**. Green ↗ "Forwarded". Muted ⊘ "Filter-blocked". Red ⚠ "Telegram rejected". | Communicate state with color alone. Even though formal a11y is out of scope per PRD §9.5, no color-only signal is the non-negotiable floor (see EXPERIENCE.md). |
| Use the `{components.banner-degraded}` at `radius: 0`, edge-to-edge, with a distinct `state-degraded` red (not `state-error`). | Use the same red for the global degraded banner as for inline field validation. The operator must learn to read banner-red as "global condition" vs. field-red as "this input." |
| Use `state-muted` for `outside_time_window` / `sampled_out` / `blocked_keyword` / `media_type_filtered` log rows. They are not errors — they are intentional suppressions. | Render filter-blocked rows in red or warning amber. That collapses "the system did what I asked" into "the system failed." |
| Use the warm-stone neutral set (`#FAFAF9` / `#14130F` and friends). | Switch to a cold zinc or cool slate neutral — the warm stone is part of the brand. |
| Keep collapsible panel headers (S3) summarizing state in `foreground-muted` text. | Let a panel header collapse without surfacing what's inside. "All collapsed by default" only works if the header *says enough*. |
