# acrylic-backend








# acrylic.la Frontend Structure

This project is currently organized for a plain `HTML`, `CSS`, and `JavaScript` frontend.

## Folder overview

```text
acrylic.la/
├── index.html
├── assets/
│   ├── audio/
│   ├── css/
│   │   ├── base/
│   │   ├── components/
│   │   ├── layout/
│   │   ├── pages/
│   │   └── main.css
│   ├── fonts/
│   ├── icons/
│   ├── images/
│   └── js/
│       ├── components/
│       ├── pages/
│       ├── utils/
│       └── main.js
├── components/
├── data/
├── docs/
└── pages/
```

## What each folder is for

- `assets/css/base`: resets, variables, typography, and global styles
- `assets/css/components`: styles for reusable UI parts like buttons, cards, navbars, and modals
- `assets/css/layout`: layout rules like header, footer, grid, and section wrappers
- `assets/css/pages`: page-specific styles
- `assets/js/components`: reusable UI behavior
- `assets/js/pages`: JavaScript used only on specific pages
- `assets/js/utils`: shared helper functions
- `assets/images`: artwork, thumbnails, illustrations, and platform graphics
- `assets/icons`: SVGs, logos, and icon files
- `assets/fonts`: local font files if you add custom branding later
- `assets/audio`: preview audio files if needed for demos or mock data
- `components`: optional HTML partials or snippets for repeated sections
- `data`: local mock JSON data during frontend development
- `docs`: notes, sitemap ideas, brand direction, and planning docs
- `pages`: additional HTML pages like `browse.html`, `pricing.html`, or `contact.html`

## Suggested next pages

- Home
- Browse catalog
- Track details
- Licensing checkout
- Creator dashboard
- Contact
