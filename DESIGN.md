---
version: alpha
name: Citefield
description: Review workspace where every extracted value points to the words on the page it was read from.
colors:
  background: "#F5F7FA"
  surface: "#FFFFFF"
  surface-raised: "#EEF1F5"
  border: "#E1E5EB"
  border-strong: "#C9D0DA"
  foreground: "#0F172A"
  muted: "#566173"
  paper: "#FFFFFF"
  sidebar: "#0F172A"
  sidebar-raised: "#1E293B"
  sidebar-foreground: "#E2E8F0"
  sidebar-muted: "#94A3B8"
  sidebar-accent: "#93B4F5"
  sidebar-review: "#FCD34D"
  primary: "#2563EB"
  primary-hover: "#1D4ED8"
  on-primary: "#FFFFFF"
  primary-fill: "#2563EB1F"
  primary-tint: "#E9F0FD"
  review: "#D97706"
  review-fg: "#92400E"
  review-fill: "#FEF3C7"
  approved: "#16A34A"
  approved-fg: "#166534"
  approved-fill: "#DCFCE7"
  corrected: "#7C3AED"
  corrected-fg: "#5B21B6"
  corrected-fill: "#EDE9FE"
  danger: "#DC2626"
  danger-fg: "#991B1B"
  danger-fill: "#FEE2E2"
  dark-background: "#0B1120"
  dark-surface: "#111827"
  dark-surface-raised: "#1A2333"
  dark-border: "#263142"
  dark-border-strong: "#364357"
  dark-foreground: "#E5E9F0"
  dark-muted: "#9AA5B8"
  dark-sidebar: "#070B14"
  dark-sidebar-raised: "#151D2C"
  dark-primary: "#5B8DEF"
  dark-primary-hover: "#7BA3F3"
  dark-review: "#C47C08"
  dark-approved: "#1AAE52"
  dark-corrected: "#9370F5"
  dark-on-primary: "#0B1120"
  dark-review-fg: "#FCD34D"
  dark-approved-fg: "#86EFAC"
  dark-corrected-fg: "#C4B5FD"
  dark-danger-fg: "#FCA5A5"
typography:
  ui:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: IBM Plex Sans
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.3
  heading:
    fontFamily: IBM Plex Sans
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.25
  metric:
    fontFamily: IBM Plex Sans
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.1
  value:
    fontFamily: IBM Plex Mono
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: 4px
  md: 6px
  lg: 10px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  section: 32px
components:
  app-canvas:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
  sidebar:
    backgroundColor: "{colors.sidebar}"
    textColor: "{colors.sidebar-foreground}"
  sidebar-item-active:
    backgroundColor: "{colors.sidebar-raised}"
    textColor: "{colors.sidebar-foreground}"
    rounded: "{rounded.md}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.lg}"
    padding: 16px
  table-header:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.muted}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: 8px
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: 8px
  status-review:
    backgroundColor: "{colors.review-fill}"
    textColor: "{colors.review-fg}"
    rounded: "{rounded.sm}"
  status-approved:
    backgroundColor: "{colors.approved-fill}"
    textColor: "{colors.approved-fg}"
    rounded: "{rounded.sm}"
  status-corrected:
    backgroundColor: "{colors.corrected-fill}"
    textColor: "{colors.corrected-fg}"
    rounded: "{rounded.sm}"
  status-failed:
    backgroundColor: "{colors.danger-fill}"
    textColor: "{colors.danger-fg}"
    rounded: "{rounded.sm}"
  field-row-active:
    backgroundColor: "{colors.primary-tint}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: 12px
  page-viewer:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.foreground}"
  page-image:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.foreground}"
  citation-box:
    backgroundColor: "{colors.primary-fill}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.sm}"
  dark-canvas:
    backgroundColor: "{colors.dark-background}"
    textColor: "{colors.dark-foreground}"
  dark-card:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-foreground}"
    rounded: "{rounded.lg}"
  dark-raised:
    backgroundColor: "{colors.dark-surface-raised}"
    textColor: "{colors.dark-muted}"
  dark-sidebar:
    backgroundColor: "{colors.dark-sidebar}"
    textColor: "{colors.sidebar-foreground}"
  dark-sidebar-item-active:
    backgroundColor: "{colors.dark-sidebar-raised}"
    textColor: "{colors.sidebar-muted}"
  dark-button-primary:
    backgroundColor: "{colors.dark-primary}"
    textColor: "{colors.dark-on-primary}"
    rounded: "{rounded.md}"
  dark-button-primary-hover:
    backgroundColor: "{colors.dark-primary-hover}"
    textColor: "{colors.dark-on-primary}"
  dark-divider:
    backgroundColor: "{colors.dark-border}"
    textColor: "{colors.dark-muted}"
  dark-divider-strong:
    backgroundColor: "{colors.dark-border-strong}"
    textColor: "{colors.dark-foreground}"
  dark-status-text:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-review-fg}"
  dark-status-approved-text:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-approved-fg}"
  dark-status-corrected-text:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-corrected-fg}"
  dark-status-failed-text:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-danger-fg}"
  divider:
    backgroundColor: "{colors.border}"
    textColor: "{colors.muted}"
  divider-strong:
    backgroundColor: "{colors.border-strong}"
    textColor: "{colors.foreground}"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  dark-chart-review:
    backgroundColor: "{colors.dark-review}"
    textColor: "{colors.dark-background}"
  dark-chart-approved:
    backgroundColor: "{colors.dark-approved}"
    textColor: "{colors.dark-background}"
  dark-chart-corrected:
    backgroundColor: "{colors.dark-corrected}"
    textColor: "{colors.dark-background}"
  status-marker-review:
    backgroundColor: "{colors.review}"
    textColor: "{colors.foreground}"
  status-marker-approved:
    backgroundColor: "{colors.approved}"
    textColor: "{colors.foreground}"
  status-marker-corrected:
    backgroundColor: "{colors.corrected}"
    textColor: "{colors.on-primary}"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
  sidebar-muted-text:
    backgroundColor: "{colors.sidebar}"
    textColor: "{colors.sidebar-muted}"
  sidebar-icon-active:
    backgroundColor: "{colors.sidebar-raised}"
    textColor: "{colors.sidebar-accent}"
  sidebar-count:
    backgroundColor: "{colors.sidebar}"
    textColor: "{colors.sidebar-review}"
---

# Citefield

## Overview

Citefield is a back-office tool. The people who use it (accounts payable, finance operations, anyone keying documents
into a system) open it every day and judge it the way they judge their accounting software: does it look like it
can be trusted with the books. The design answers that, not the portfolio.

- **Mood:** an audit file. Calm, precise, light, dense where data is dense. Nothing on screen is decorative; every
  colour either marks evidence or marks a status.
- **Differentiating detail:** the citation box. The active field's value is drawn on the page as a blue outline with
  a translucent fill around the exact words it came from, and a thin leader line joins it to the field row. The
  product's claim, "every value points to its words", is visible on the review screen instead of described.
- **Opts out of the global dark glassmorphism default** (DESIGN.md wins): no gradient mesh, no glow. Enterprise review
  tools are read for hours on light screens next to spreadsheets; the earlier dark indigo look read as a demo. Dark is
  a designed second theme, chosen in Settings or by the system, not the identity.
- **Layout family:** application shell. A navy sidebar (Overview, Documents, Needs review, Schemas, Settings) and a
  light content canvas. Overview is an asymmetric split (one wide work card, one narrow metric) over a chart row;
  Documents is a dense index; Review is a 7/5 split with the page on the left.

## Colors

- Neutrals carry the screen: `background` canvas, white `surface` cards with a hairline `border`, `surface-raised`
  for table headers, hovers and the page viewer's well.
- `primary` (blue) is the one accent: primary actions, links, focus, and citation boxes. It is never a status.
- Status colours carry meaning and nothing else, each with three tones: the strong tone (`review`, `approved`,
  `corrected`, `danger`) for box strokes and dots, the `-fill` tone for badge backgrounds, the `-fg` tone for text on
  that fill (4.5:1 or better). `review` amber needs a person, `approved` green passed every check or was confirmed,
  `corrected` violet was changed by a person, `danger` is for failed documents and destructive actions. Status is never
  colour alone: every badge has a word.
- `paper` is the page image itself, shown unfiltered on the `surface-raised` well.
- The status trio was run through the dataviz palette validator (light on white, dark on `dark-surface`): all checks
  pass. An earlier teal for `corrected` sat 10.8 ΔE from `approved` and failed the normal-vision floor, so it moved to
  violet. `auto` is the neutral `border-strong` on purpose: nothing happened to it, and it is always labelled.
- Boxes on the page image use the light strong tones in both themes: the paper is white either way.
- Dark theme: `dark-*` tokens replace their light names. Surfaces get lighter as they rise, accents are desaturated,
  status fills become 15% tints of the strong tone under the `dark-*-fg` text.

## Typography

- IBM Plex Sans for the interface, IBM Plex Mono for extracted values, ids and amounts: values are data, and
  monospaced digits line up when amounts are compared down a column. Tabular figures everywhere numbers sit in a table.
- `metric` is reserved for the overview's headline numbers. Page titles use `heading`; section titles inside cards use
  `label` in the foreground colour, never all caps.
- Fonts are bundled with the app (`@fontsource`), never loaded from a CDN: self-hosted installs make no outside
  requests.

## Layout

- Sidebar 240px from 1024px up; below that a top bar with a menu button opens it as a drawer.
- Content max width 1440px with 24px gutters (16px on phones). Cards sit 16px apart, sections 32px.
- Review: page viewer at least 55% of the width on desktop; below 1024px the panes stack and the page comes first.
- Tables keep a 40px row height; the first column is the object (file name), the last its actions.

## Components

- **Cards** are flat: white, hairline border, `rounded.lg`, no shadow. Only menus, dialogs and popovers cast a shadow.
- **Field panel:** fields that need review come first under a "Needs review" heading with a count; each shows its
  reasons as plain sentences under the value. Line items render as a grid, one row per item number. Schema fields the
  document did not contain are listed as "Not found", so a missing value is visible, not silent.
- **Blocker summary** at the top of a document: how many fields wait and which checks sent them, each a chip that
  jumps to its first field.
- **Selection** is a 1px primary ring plus the primary fill, not a coloured side strip.
- **Re-cite mode:** page words become hoverable outlines; clicked words join the selection; the box updates live.
- **Keyboard first:** `j`/`k` move between fields, `a` approves, `e` edits, `c` re-cites, `Enter` saves, `Esc`
  cancels, `[`/`]` previous and next document that needs review, `?` lists the shortcuts. Every action also has a
  visible button.
- **Charts** are plain SVG bars in the neutral ramp with one highlighted series; every chart has its numbers in text.

## Do's and Don'ts

- Do keep the page image unfiltered: no blur, tint or overlay on the paper except citation boxes.
- Do give every empty state one next action (upload, open the next document, create a schema).
- Don't show a confidence percentage as the reason for a decision; show the trigger sentences the verifier produced.
- Don't use gradients, glows or coloured side strips; depth is a hairline border and a step in surface tone.
- Don't load fonts, icons or scripts from third-party hosts.
