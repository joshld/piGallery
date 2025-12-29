# Adding New Themes to themes.css

Adding a new theme to `themes.css` is very straightforward! Here's how:

## Steps to Add a New Theme

1. **Open `static/themes.css`** in your editor

2. **Add a new theme block** at the end of the file (before the closing brace, if any). The format is:

```css
html[data-theme="your-theme-name"] {
    --bg-primary: /* your background gradient or color */;
    --bg-card: /* card background */;
    --bg-input: /* input background */;
    --text-primary: /* main text color */;
    --text-secondary: /* secondary text color */;
    --accent-primary: /* primary accent color */;
    --accent-secondary: /* secondary accent color */;
    /* ... and so on for all CSS variables */
}
```

3. **Copy an existing theme** (like `light` or `dark`) as a template and modify the color values

4. **Add the theme name to the dropdown** in `static/index.html` - find the `<select id="theme-selector">` and add:
   ```html
   <option value="your-theme-name">Your Theme Name</option>
   ```

5. **That's it!** The theme will automatically be available in the theme selector dropdown.

## Example: Adding a "Sunset" Theme

```css
html[data-theme="sunset"] {
    --bg-primary: linear-gradient(135deg, #ff6b6b 0%, #ffa500 100%);
    --bg-card: #fff5e6;
    --bg-input: #ffffff;
    --text-primary: #2c1810;
    --text-secondary: #5c3d2e;
    --accent-primary: #ff6b6b;
    --accent-secondary: #ff8c42;
    /* ... copy remaining variables from another theme and adjust colors */
}
```

Then add to the dropdown:
```html
<option value="sunset">Sunset</option>
```

## CSS Variables Reference

All themes use the same CSS variables. You can see the complete list by looking at any existing theme in `themes.css`. The main categories are:

- **Backgrounds**: `--bg-primary`, `--bg-card`, `--bg-input`, `--bg-hover`, etc.
- **Text**: `--text-primary`, `--text-secondary`, `--text-header`, etc.
- **Accents**: `--accent-primary`, `--accent-secondary`, `--accent-border`, etc.
- **Shadows**: `--shadow-card`, `--shadow-button`, `--shadow-modal`, etc.
- **Borders**: `--border-divider`, `--border-setting`, etc.

## Tips

- Use color picker tools or theme generators to get harmonious color palettes
- Test your theme in both light and dark viewing conditions
- Make sure text has sufficient contrast for readability
- Button colors should match the overall aesthetic of your theme
