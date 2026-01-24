# Material Design 3 Layout Guidelines

## Responsive Breakpoints

| Window Class | Breakpoint | Columns | Margins | Gutter |
|--------------|------------|---------|---------|--------|
| Compact | 0-599dp | 4 | 16dp | 8dp |
| Medium | 600-839dp | 8 | 24dp | 16dp |
| Expanded | 840-1199dp | 12 | 24dp | 24dp |
| Large | 1200-1599dp | 12 | 24dp | 24dp |
| Extra Large | 1600dp+ | 12 | 24dp | 24dp |

## Grid System

```css
.md-grid {
  display: grid;
  gap: var(--md-gutter);
  padding: 0 var(--md-margin);
}

/* Compact */
@media (max-width: 599px) {
  :root {
    --md-columns: 4;
    --md-margin: 16px;
    --md-gutter: 8px;
  }
}

/* Medium */
@media (min-width: 600px) and (max-width: 839px) {
  :root {
    --md-columns: 8;
    --md-margin: 24px;
    --md-gutter: 16px;
  }
}

/* Expanded */
@media (min-width: 840px) {
  :root {
    --md-columns: 12;
    --md-margin: 24px;
    --md-gutter: 24px;
  }
}
```

## Canonical Layouts

### List-Detail
- **Compact**: Single pane, navigate between list and detail
- **Medium/Expanded**: Side-by-side panels

```
┌─────────────────────────────────┐
│  List   │       Detail          │
│  (1/3)  │       (2/3)           │
│         │                       │
└─────────────────────────────────┘
```

### Feed
- **Compact**: Single column
- **Medium**: 2 columns
- **Expanded**: 2-3 columns with fixed content area

### Supporting Pane
- **Compact**: Bottom sheet or full screen
- **Medium/Expanded**: Side panel (320-360dp)

## Navigation Patterns

| Screen Size | Primary Navigation |
|-------------|-------------------|
| Compact (< 600dp) | Bottom navigation bar |
| Medium (600-839dp) | Navigation rail |
| Expanded (840dp+) | Navigation drawer |

## Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4dp | Tight spacing |
| sm | 8dp | Related elements |
| md | 16dp | Standard spacing |
| lg | 24dp | Section spacing |
| xl | 32dp | Large gaps |
| 2xl | 48dp | Major sections |

## Content Width

- **Maximum content width**: 840-1040dp for readability
- **Center content** on larger screens
- **Use margins** to prevent edge-to-edge content

```css
.md-content {
  max-width: 840px;
  margin: 0 auto;
  padding: 0 var(--md-margin);
}
```

## App Bar Layouts

### Top App Bar
- **Height**: 64dp (compact), 64dp (medium/expanded)
- **Elevation**: Level 0-2 based on scroll

### Variants
1. **Center-aligned**: Logo/title centered
2. **Small**: Title left-aligned
3. **Medium**: Two-line with larger title
4. **Large**: Prominent header with large title

```css
.md-top-app-bar {
  height: 64px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  background: var(--md-sys-color-surface);
}
.md-top-app-bar-large {
  height: 152px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-end;
  padding-bottom: 28px;
}
```

## Pane Behavior

### Fixed Pane
- Stays in place during scroll
- Use for navigation, toolbars

### Scrolling Pane
- Scrolls with content
- Use for primary content area

### Collapsing Pane
- Shrinks on scroll
- Use for app bars, headers

## Touch Targets

- **Minimum size**: 48x48dp
- **Recommended size**: 48x48dp with 8dp spacing
- **Icons**: 24dp with 48dp touch target

```css
.md-touch-target {
  min-width: 48px;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

## Z-Index Layers

| Layer | Z-Index | Elements |
|-------|---------|----------|
| Base | 0 | Content |
| Elevated | 1-5 | Cards, buttons |
| Navigation | 10 | App bars, nav |
| Modal | 20 | Dialogs, sheets |
| Overlay | 30 | Scrim |
| Toast | 40 | Snackbars |
| Tooltip | 50 | Tooltips |
