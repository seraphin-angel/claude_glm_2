# Material Design 3 Components

## Buttons

### Filled Button
- **Use**: High-emphasis actions
- **Shape**: Medium (12dp radius)
- **Height**: 40dp
- **Padding**: 24dp horizontal
- **Color**: primary / on-primary

```css
.md-filled-button {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  border-radius: 20px;
  height: 40px;
  padding: 0 24px;
  font: var(--md-sys-typescale-label-large);
}
```

### Tonal Button
- **Use**: Medium-emphasis actions
- **Color**: secondary-container / on-secondary-container

### Outlined Button
- **Use**: Medium-emphasis, secondary actions
- **Border**: 1dp outline color

### Text Button
- **Use**: Low-emphasis actions
- **Color**: primary (no background)

### FAB (Floating Action Button)
- **Sizes**: Small (40dp), Regular (56dp), Large (96dp)
- **Shape**: Large (16dp radius)
- **Color**: primary-container / on-primary-container

## Cards

### Elevated Card
- **Elevation**: Level 1 (1dp)
- **Shape**: Medium (12dp radius)
- **Color**: surface-container-low

### Filled Card
- **Elevation**: Level 0
- **Shape**: Medium (12dp radius)
- **Color**: surface-container-highest

### Outlined Card
- **Elevation**: Level 0
- **Border**: 1dp outline-variant
- **Color**: surface

```css
.md-card {
  border-radius: 12px;
  padding: 16px;
}
.md-card-elevated {
  background: var(--md-sys-color-surface-container-low);
  box-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
.md-card-filled {
  background: var(--md-sys-color-surface-container-highest);
}
.md-card-outlined {
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
}
```

## Text Fields

### Filled Text Field
- **Shape**: Extra Small top (4dp), None bottom
- **Color**: surface-container-highest
- **Indicator**: 2dp bottom border (primary when focused)

### Outlined Text Field
- **Shape**: Extra Small (4dp)
- **Border**: 1dp outline (primary when focused)

```css
.md-text-field {
  height: 56px;
  padding: 0 16px;
}
.md-text-field-filled {
  background: var(--md-sys-color-surface-container-highest);
  border-radius: 4px 4px 0 0;
  border-bottom: 1px solid var(--md-sys-color-on-surface-variant);
}
.md-text-field-outlined {
  background: transparent;
  border-radius: 4px;
  border: 1px solid var(--md-sys-color-outline);
}
```

## Navigation

### Navigation Bar (Bottom)
- **Height**: 80dp
- **Items**: 3-5 destinations
- **Icon**: 24dp
- **Active indicator**: secondary-container (64dp x 32dp pill)

### Navigation Rail (Side)
- **Width**: 80dp
- **Use**: Medium screens (600-840dp)

### Navigation Drawer
- **Width**: 360dp max
- **Use**: Large screens (840dp+)

## Chips

### Assist Chip
- **Use**: Smart suggestions
- **Height**: 32dp
- **Shape**: Small (8dp radius)

### Filter Chip
- **Use**: Filtering content
- **Selected**: secondary-container

### Input Chip
- **Use**: User input representation
- **Removable**: trailing X icon

### Suggestion Chip
- **Use**: Dynamically generated suggestions

```css
.md-chip {
  height: 32px;
  border-radius: 8px;
  padding: 0 16px;
  font: var(--md-sys-typescale-label-large);
}
.md-chip-assist {
  background: var(--md-sys-color-surface-container-low);
  border: 1px solid var(--md-sys-color-outline);
}
.md-chip-filter-selected {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}
```

## Dialogs

### Basic Dialog
- **Width**: 280-560dp
- **Shape**: Extra Large (28dp radius)
- **Elevation**: Level 3
- **Padding**: 24dp

```css
.md-dialog {
  background: var(--md-sys-color-surface-container-high);
  border-radius: 28px;
  padding: 24px;
  min-width: 280px;
  max-width: 560px;
}
```

## Lists

### List Item
- **Height**: One-line (56dp), Two-line (72dp), Three-line (88dp)
- **Leading**: 24dp icon or 40dp avatar
- **Trailing**: Icon, text, or checkbox

```css
.md-list-item {
  padding: 8px 16px;
  min-height: 56px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.md-list-item:hover {
  background: var(--md-sys-color-on-surface);
  opacity: 0.08;
}
```

## Menus

### Menu
- **Shape**: Extra Small (4dp radius)
- **Elevation**: Level 2
- **Width**: 112-280dp
- **Item height**: 48dp

## Snackbars

- **Position**: Bottom center
- **Shape**: Extra Small (4dp radius)
- **Color**: inverse-surface / inverse-on-surface
- **Duration**: 4-10 seconds

```css
.md-snackbar {
  background: var(--md-sys-color-inverse-surface);
  color: var(--md-sys-color-inverse-on-surface);
  border-radius: 4px;
  padding: 14px 16px;
  min-width: 288px;
  max-width: 568px;
}
```

## Tabs

### Primary Tabs
- **Height**: 48dp
- **Indicator**: 3dp underline (primary)
- **Use**: Top-level destinations

### Secondary Tabs
- **Height**: 48dp
- **Indicator**: Full-width underline
- **Use**: Content organization within page

## Switches

- **Track size**: 52dp x 32dp
- **Thumb size**: 16dp (off), 24dp (on)
- **Selected**: primary (track), on-primary (thumb)

## Progress Indicators

### Linear
- **Height**: 4dp
- **Color**: primary (indicator), surface-container-highest (track)

### Circular
- **Size**: 40dp (standard), 48dp (large)
- **Stroke**: 4dp
