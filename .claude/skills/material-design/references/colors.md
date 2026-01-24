# Material Design 3 Color System

## Tonal Palette Structure

M3 generates 13 tonal values (0-100) for each color:

```
0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 100
```

- **0** = Pure black
- **100** = Pure white
- **40** = Typical primary color in light theme
- **80** = Typical primary color in dark theme

## Color Roles

### Primary Colors
```css
--md-sys-color-primary: /* Tone 40 (light) / 80 (dark) */
--md-sys-color-on-primary: /* Tone 100 (light) / 20 (dark) */
--md-sys-color-primary-container: /* Tone 90 (light) / 30 (dark) */
--md-sys-color-on-primary-container: /* Tone 10 (light) / 90 (dark) */
```

### Secondary Colors
```css
--md-sys-color-secondary: /* Tone 40 (light) / 80 (dark) */
--md-sys-color-on-secondary: /* Tone 100 (light) / 20 (dark) */
--md-sys-color-secondary-container: /* Tone 90 (light) / 30 (dark) */
--md-sys-color-on-secondary-container: /* Tone 10 (light) / 90 (dark) */
```

### Tertiary Colors
```css
--md-sys-color-tertiary: /* Tone 40 (light) / 80 (dark) */
--md-sys-color-on-tertiary: /* Tone 100 (light) / 20 (dark) */
--md-sys-color-tertiary-container: /* Tone 90 (light) / 30 (dark) */
--md-sys-color-on-tertiary-container: /* Tone 10 (light) / 90 (dark) */
```

### Surface Colors
```css
--md-sys-color-surface: /* Tone 99 (light) / 10 (dark) */
--md-sys-color-on-surface: /* Tone 10 (light) / 90 (dark) */
--md-sys-color-surface-variant: /* Tone 90 (light) / 30 (dark) */
--md-sys-color-on-surface-variant: /* Tone 30 (light) / 80 (dark) */
```

### Surface Container Hierarchy
```css
--md-sys-color-surface-container-lowest: /* Tone 100 (light) / 4 (dark) */
--md-sys-color-surface-container-low: /* Tone 96 (light) / 10 (dark) */
--md-sys-color-surface-container: /* Tone 94 (light) / 12 (dark) */
--md-sys-color-surface-container-high: /* Tone 92 (light) / 17 (dark) */
--md-sys-color-surface-container-highest: /* Tone 90 (light) / 22 (dark) */
```

### Error Colors
```css
--md-sys-color-error: /* Red tone 40 (light) / 80 (dark) */
--md-sys-color-on-error: /* Tone 100 (light) / 20 (dark) */
--md-sys-color-error-container: /* Red tone 90 (light) / 30 (dark) */
--md-sys-color-on-error-container: /* Red tone 10 (light) / 90 (dark) */
```

### Outline Colors
```css
--md-sys-color-outline: /* Tone 50 (light) / 60 (dark) */
--md-sys-color-outline-variant: /* Tone 80 (light) / 30 (dark) */
```

## Dynamic Color

Dynamic color extracts colors from user wallpaper or content:

1. **Source color** - Extracted dominant color
2. **Tonal palettes** - Generated primary, secondary, tertiary, neutral, error
3. **Color scheme** - Applied based on light/dark mode

## Example Light Theme

```css
:root {
  /* Primary */
  --md-sys-color-primary: #6750A4;
  --md-sys-color-on-primary: #FFFFFF;
  --md-sys-color-primary-container: #EADDFF;
  --md-sys-color-on-primary-container: #21005D;

  /* Secondary */
  --md-sys-color-secondary: #625B71;
  --md-sys-color-on-secondary: #FFFFFF;
  --md-sys-color-secondary-container: #E8DEF8;
  --md-sys-color-on-secondary-container: #1D192B;

  /* Tertiary */
  --md-sys-color-tertiary: #7D5260;
  --md-sys-color-on-tertiary: #FFFFFF;
  --md-sys-color-tertiary-container: #FFD8E4;
  --md-sys-color-on-tertiary-container: #31111D;

  /* Surface */
  --md-sys-color-surface: #FFFBFE;
  --md-sys-color-on-surface: #1C1B1F;
  --md-sys-color-surface-variant: #E7E0EC;
  --md-sys-color-on-surface-variant: #49454F;

  /* Error */
  --md-sys-color-error: #B3261E;
  --md-sys-color-on-error: #FFFFFF;
  --md-sys-color-error-container: #F9DEDC;
  --md-sys-color-on-error-container: #410E0B;

  /* Outline */
  --md-sys-color-outline: #79747E;
  --md-sys-color-outline-variant: #CAC4D0;

  /* Background */
  --md-sys-color-background: #FFFBFE;
  --md-sys-color-on-background: #1C1B1F;
}
```

## Example Dark Theme

```css
:root[data-theme="dark"] {
  /* Primary */
  --md-sys-color-primary: #D0BCFF;
  --md-sys-color-on-primary: #381E72;
  --md-sys-color-primary-container: #4F378B;
  --md-sys-color-on-primary-container: #EADDFF;

  /* Secondary */
  --md-sys-color-secondary: #CCC2DC;
  --md-sys-color-on-secondary: #332D41;
  --md-sys-color-secondary-container: #4A4458;
  --md-sys-color-on-secondary-container: #E8DEF8;

  /* Tertiary */
  --md-sys-color-tertiary: #EFB8C8;
  --md-sys-color-on-tertiary: #492532;
  --md-sys-color-tertiary-container: #633B48;
  --md-sys-color-on-tertiary-container: #FFD8E4;

  /* Surface */
  --md-sys-color-surface: #1C1B1F;
  --md-sys-color-on-surface: #E6E1E5;
  --md-sys-color-surface-variant: #49454F;
  --md-sys-color-on-surface-variant: #CAC4D0;

  /* Error */
  --md-sys-color-error: #F2B8B5;
  --md-sys-color-on-error: #601410;
  --md-sys-color-error-container: #8C1D18;
  --md-sys-color-on-error-container: #F9DEDC;

  /* Outline */
  --md-sys-color-outline: #938F99;
  --md-sys-color-outline-variant: #49454F;

  /* Background */
  --md-sys-color-background: #1C1B1F;
  --md-sys-color-on-background: #E6E1E5;
}
```

## Color Usage Guidelines

| Component | Color Role |
|-----------|------------|
| Primary button | primary / on-primary |
| Secondary button | secondary-container / on-secondary-container |
| FAB | primary-container / on-primary-container |
| Card | surface-container / on-surface |
| App bar | surface / on-surface |
| Navigation | surface-container / on-surface-variant |
| Text field | surface-container-highest / on-surface |
| Chip (selected) | secondary-container / on-secondary-container |
| Chip (unselected) | surface-container-low / on-surface-variant |
