---
name: Precision Operations
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#434655'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#006242'
  on-tertiary: '#ffffff'
  tertiary-container: '#007d55'
  on-tertiary-container: '#bdffdb'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
  data-mono:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: -0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system is engineered for boutique consultancies, engineering practices, and specialized modern service firms where speed, density, and operational clarity dictate performance. The brand persona is disciplined, analytical, and uncluttered—delivering the utilitarian rigor of advanced operating infrastructure without unnecessary decorative distraction.

The visual style merges structured Modern Corporate architecture with high-density European utilitarianism. Surfaces are clean, contrast ratios exceed standard accessibility baselines, and layout hierarchy is governed by strict mathematical rhythm. The aesthetic instills total confidence, quiet competence, and relentless efficiency across fast-paced daily client work and pipeline governance.

## Colors

The palette establishes an authoritative, daylight-balanced foundation optimized for sustained daylight monitor usage.

- **Primary (`#2563EB`)**: Deep operational cobalt. Used for focal callouts, active operational states, focused table selections, and primary command triggers.
- **Secondary (`#0F172A`)**: Midnight slate. Delivers high-density readability across primary typography, structural borders, and persistent navigation anchors.
- **Tertiary (`#10B981`)**: Precision emerald. Reserved for positive deltas, paid status, health indicators, and finalized milestones.
- **Neutral (`#64748B`)**: Cool slate. Governs structural hairline borders (`#E2E8F0`), secondary surface tints (`#F8FAFC`), and supporting metadata labels.

### Functional Status System
- **Active / Success**: `#059669` text on `#ECFDF5` background with `#A7F3D0` border.
- **Pending / In Progress**: `#D97706` text on `#FFFBEB` background with `#FDE68A` border.
- **Overdue / Critical**: `#E11D48` text on `#FFF1F2` background with `#FECDD3` border.

## Typography

The type hierarchy relies entirely on Inter to maintain visual coherence across high-density data matrices, operational tables, and dashboard telemetry. 

- Numeric values and financial ledgers enforce tabular figures (`font-feature-settings: 'tnum' 1, 'cv05' 1`) to preserve vertical scanning alignment.
- Labels utilize tight tracking with uppercase or semi-bold treatment to anchor data fields without increasing vertical row heights.
- Headings are compact with tight negative tracking to prevent awkward line breaks in dense master-detail views.

## Layout & Spacing

This design system uses a flexible 12-column grid system bounded by fixed toolbars and variable side-rail navigation patterns.

- **Desktop (1280px+)**: 12 columns, 1rem gutters, fixed 240px or collapsible 64px left rail, 1.5rem external margins. High-density grids accommodate multiple side-by-side data panes (e.g., deal board alongside activity stream).
- **Tablet (768px - 1279px)**: 8 columns, 1rem gutters, auto-collapsing navigation into a slim rail or slide-over drawer, 1rem external margins.
- **Mobile (<768px)**: 4 columns, 0.75rem gutters, bottom navigation bar or slide sheet, 1rem external margins. Complex data grids fold into stacked analytical cards.

The vertical rhythm is calibrated around 4px micro-increments, prioritizing compact component heights (32px to 36px inputs and action triggers) to maximize visible data above the fold.

## Elevation & Depth

Visual hierarchy is maintained through crisp hairline borders paired with diffused, low-opacity ambient drop shadows. Surfaces do not rely on aggressive z-axis elevation, preserving an editorial, sheet-metal feel.

- **Base Layer (Canvas)**: Background canvas sits at `#F8FAFC`.
- **Card & Container Layer**: Raised workspace panels sit at `#FFFFFF`, bounded by a 1px continuous border (`#E2E8F0`) and softened with a dual ambient shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.02)`.
- **Dropdown & Flyout Layer**: Popovers and contextual action menus feature `0 10px 15px -3px rgba(15, 23, 42, 0.06), 0 4px 6px -4px rgba(15, 23, 42, 0.03)` with a structural border (`#CBD5E1`).
- **Modal & Sheet Layer**: Floating focus surfaces use a deep perimeter blur: `0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.04)` over a backdrop tint of `rgba(15, 23, 42, 0.4)`.

## Shapes

The interface balances precision-engineered straight lines with intentional softness. Primary data cards, dashboards, and modal dialogs adopt `rounded-xl` (1.5rem / 24px outer corner bounds), creating a polished frame for internal structural elements.

Interior interactive components use restrained radii to conserve screen real estate:
- **Buttons, inputs, and segmented controls**: 0.375rem (6px) to 0.5rem (8px).
- **Badges, metadata tags, and status pills**: Fully rounded pill shapes (`9999px`) to immediately distinguish actionable data tokens from static structural cards.

## Components

### Buttons
- **Primary**: Solid `#2563EB`, text `#FFFFFF`, subtle inset top highlight, 0.5rem radius, height 36px (dense: 32px). Hover: `#1D4ED8`. Active: `#1E40AF`.
- **Secondary**: Surface `#FFFFFF`, border 1px solid `#CBD5E1`, text `#0F172A`. Hover: `#F8FAFC` and border `#94A3B8`.
- **Tertiary / Ghost**: Transparent, text `#475569`. Hover: `#F1F5F9`, text `#0F172A`.

### Status Pills & Chips
- Fully rounded (`9999px`), 20px height, padding 0.125rem 0.5rem. Text is `label-sm`.
- Formatted as subtle tinted backgrounds with high-contrast text and a matched 1px perimeter border (e.g., active client status: background `#ECFDF5`, text `#065F46`, border `#A7F3D0`).

### Input Fields & Selects
- Height 36px, background `#FFFFFF`, border 1px solid `#CBD5E1`, font `body-md`.
- Focus: Border `#2563EB`, box-shadow `0 0 0 3px rgba(37, 99, 235, 0.15)`, outline none.
- Leading icon slots standardized at 16px with `#64748B` fill.

### Tables & Dense Lists
- Row height: 40px (default), 32px (compact audit mode).
- Header: `#F8FAFC`, uppercase `label-sm`, text `#475569`, border-bottom 1px solid `#E2E8F0`.
- Cell borders: 1px horizontal separator `#F1F5F9`. Hover state on row: `#F8FAFC`.

### Checkboxes & Radio Buttons
- 16px × 16px, 4px corner radius for checkboxes, full circle for radios.
- Unchecked: `#FFFFFF` with 1px border `#CBD5E1`.
- Checked: `#2563EB` fill with crisp white glyph centered.

### Cards & Container Panels
- Background `#FFFFFF`, 1px solid border `#E2E8F0`, corner radius `rounded-xl`.
- Padding: 1.25rem internal padding with dedicated header sub-sections separated by a 1px border line.

### Operational Key-Value Pairs
- Compact horizontal layouts featuring `label-sm` in `#64748B` aligned against right-justified or adjacent `data-mono` values in `#0F172A`.