---
name: material-design
description: Google Material Design 3 guidelines for creating beautiful, accessible, and consistent user interfaces. Use when building UI components, designing color schemes, applying typography, creating layouts, or styling any web/mobile application following Material Design principles. Triggers on requests for Material Design, M3, Material You, Google design system, or UI/UX design following Google guidelines.
---

# Material Design 3

Apply Google's Material Design 3 (M3) system to create expressive, accessible, and consistent user interfaces.

## Core Principles

1. **Personal** - Dynamic color adapts to user preferences
2. **Adaptive** - Responsive layouts for all screen sizes
3. **Expressive** - Vibrant styles with emotional impact

## Quick Reference

### Color System

M3 uses a tonal palette system with key color roles:

| Role | Usage |
|------|-------|
| Primary | Key components, active states |
| Secondary | Less prominent components |
| Tertiary | Contrasting accents |
| Surface | Backgrounds, cards |
| Error | Error states, destructive actions |

Each role has container and on-container variants (e.g., `primary`, `on-primary`, `primary-container`, `on-primary-container`).

### Typography Scale

| Style | Size | Weight | Use Case |
|-------|------|--------|----------|
| Display Large | 57px | 400 | Hero text |
| Display Medium | 45px | 400 | Large headers |
| Display Small | 36px | 400 | Section headers |
| Headline Large | 32px | 400 | Page titles |
| Headline Medium | 28px | 400 | Card titles |
| Headline Small | 24px | 400 | Subsections |
| Title Large | 22px | 400 | Dialog titles |
| Title Medium | 16px | 500 | List headers |
| Title Small | 14px | 500 | Tabs |
| Body Large | 16px | 400 | Primary content |
| Body Medium | 14px | 400 | Secondary content |
| Body Small | 12px | 400 | Captions |
| Label Large | 14px | 500 | Buttons |
| Label Medium | 12px | 500 | Navigation |
| Label Small | 11px | 500 | Badges |

### Shape Scale

| Category | Corner Radius |
|----------|---------------|
| None | 0dp |
| Extra Small | 4dp |
| Small | 8dp |
| Medium | 12dp |
| Large | 16dp |
| Extra Large | 28dp |
| Full | 50% (circular) |

### Elevation Levels

| Level | Elevation | Usage |
|-------|-----------|-------|
| 0 | 0dp | Flat surfaces |
| 1 | 1dp | Cards, search bars |
| 2 | 3dp | Buttons, menus |
| 3 | 6dp | FABs, navigation drawers |
| 4 | 8dp | Side sheets |
| 5 | 12dp | Dialogs, modals |

## Detailed Guides

- **Color system details**: See [references/colors.md](references/colors.md)
- **Component specifications**: See [references/components.md](references/components.md)
- **Layout guidelines**: See [references/layout.md](references/layout.md)

## Implementation Workflow

1. Define brand colors using the M3 color system
2. Generate tonal palettes from source colors
3. Apply typography scale consistently
4. Use appropriate elevation and shape for components
5. Ensure color contrast meets accessibility standards (WCAG 2.1 AA minimum)

## Accessibility Requirements

- Maintain 4.5:1 contrast ratio for normal text
- Maintain 3:1 contrast ratio for large text and UI components
- Support reduced motion preferences
- Provide sufficient touch targets (minimum 48x48dp)
