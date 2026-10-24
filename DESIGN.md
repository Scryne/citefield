---
version: alpha
name: Citefield
description: Review workspace where every extracted value points to the words on the page it was read from.
colors:
  background: "#0B0D17"
  background-glow-1: "#2A1B4D"
  background-glow-2: "#0F2A4A"
  surface: "#141726"
  surface-raised: "#1C2033"
  border: "#2C3150"
  foreground: "#EEF0F8"
  muted: "#9AA0BC"
  paper: "#FFFFFF"
  primary: "#6E7BFF"
  primary-fill: "#6E7BFF33"
  review: "#FFB224"
  approved: "#3DD68C"
  corrected: "#4CC3FF"
  danger: "#FF5A5F"
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
    letterSpacing: 0.02em
  heading:
    fontFamily: IBM Plex Sans
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.25
  value:
    fontFamily: IBM Plex Mono
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: 4px
  md: 8px
  lg: 12px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
components:
  field-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: 12px
  field-row-active:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: 12px
  status-review:
    backgroundColor: "{colors.review}"
    textColor: "{colors.background}"
    rounded: "{rounded.sm}"
  status-approved:
    backgroundColor: "{colors.approved}"
    textColor: "{colors.background}"
    rounded: "{rounded.sm}"
  status-corrected:
    backgroundColor: "{colors.corrected}"
    textColor: "{colors.background}"
    rounded: "{rounded.sm}"
  status-failed:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.background}"
    rounded: "{rounded.sm}"
  field-reason:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.background}"
    rounded: "{rounded.md}"
    padding: 8px
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: 8px
  page-viewer:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.background}"
  citation-box:
    backgroundColor: "{colors.primary-fill}"
    textColor: "{colors.background}"
    rounded: "{rounded.sm}"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.lg}"
  divider:
    backgroundColor: "{colors.border}"
    textColor: "{colors.muted}"
  workspace:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
  workspace-glow:
    backgroundColor: "{colors.background-glow-1}"
    textColor: "{colors.foreground}"
  workspace-glow-2:
    backgroundColor: "{colors.background-glow-2}"
    textColor: "{colors.foreground}"
---

# Citefield

## Overview

The global base (dark glassmorphism: blur, light-catcher border, contrast, performance) applies; this file records
only what is particular to Citefield.

- **Mood:** an evidence desk at night. A dark, quiet workspace whose single bright object is the document page, the
  way a reading lamp lights paper. Everything else steps back so the page and its marked words carry the screen.
- **Differentiating detail:** the citation box. The active field's value is drawn on the page as an indigo outline
  with a translucent fill around the exact OCR words it came from, and a thin leader line joins it to the field row.
  The product's claim, "every value points to its words", is visible on every screen instead of described.

## Colors

- `paper` is reserved for the page image area; no other surface is white, so the page reads as the subject.
- `primary` (indigo) is the one accent, the citation colour. It marks evidence (boxes, the active row edge, the primary action). It was chosen to stay
  distinct on white paper and on the dark surfaces, and to never be confused with a status.
- Status colours carry meaning and nothing else: `review` (amber) needs a person, `approved` (green) was confirmed or
  passed every check, `corrected` (cyan) was changed by a person, `danger` is for failed documents and destructive
  actions. Status is never shown by colour alone: each badge has a word.
- The background is the global gradient mesh, toned down to two deep glows (`background-glow-1`, `background-glow-2`)
  behind the panels; it must never compete with the page.

## Typography

- IBM Plex Sans for the interface, IBM Plex Mono for extracted values, word ids and amounts: values are data, and
  monospaced digits line up when amounts are compared down a column.
- Fonts are bundled with the app (`@fontsource`), never loaded from a CDN: self-hosted installs must make no outside
  requests.

## Components

- **Layout:** two panes. Left: the page viewer (zoom, page switcher), at least 55% of the width on desktop. Right: the
  field panel. Below 900px the panes stack and the page viewer becomes a collapsible sheet above the fields.
- **Field panel:** fields that need review come first, grouped under a "Needs review" heading with a count; each
  shows its reasons as plain sentences under the value. Approved and automatic fields follow, collapsed by group.
  Line items render as a compact table, one row per item number.
- **Glass:** only the top bar and the field panel's sticky header use the blur surface. Field rows are solid `surface`.
- **Re-cite mode:** when a reviewer re-cites a value, page words become hoverable outlines; clicked words join the
  selection; the box updates live.
- **Keyboard first:** `j`/`k` move between fields, `a` approves, `e` edits, `c` re-cites, `Enter` saves, `Esc`
  cancels. Every action has a visible button too.

## Do's and Don'ts

- Do keep the page image unfiltered: no blur, tint or overlay on the paper except citation boxes.
- Don't animate blur, and don't put more than two blurred layers on screen.
- Don't show a confidence percentage as the reason for a decision; show the trigger sentences the verifier produced.
- Don't load fonts, icons or scripts from third-party hosts.
