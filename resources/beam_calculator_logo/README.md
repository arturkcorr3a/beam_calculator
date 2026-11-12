# beam_calculator — logo files

"b" monogram: the letter is formed by a beam cross-section, and the dots represent the positive reinforcement bars.
In the SVGs, the text has been converted to outlines, so they render identically on any computer without installing fonts.

## Folders

| Folder | Contents |
|---|---|
| `svg/symbol`, `png/symbol` | Monogram only (PNG at 256, 512 and 1024 px) |
| `svg/horizontal`, `png/horizontal` | Symbol + name, with and without the tagline "Dimensionamento de vigas em concreto armado" (reinforced concrete beam design) (PNG @2x and @4x) |
| `svg/vertical`, `png/vertical` | Stacked version, for covers and title pages |
| `svg/icon`, `png/icon` | App icon, favicons (16/32/48 px and `.ico`), `apple-touch-icon` and Android icons |

Each logo comes in four versions:
- `color`: for light backgrounds
- `negative`: for dark backgrounds
- `mono-black`: black-and-white printing
- `mono-white`: application over photos or dark colors

All PNGs have a transparent background, except the app icons.

## Colors

| Use | Hex |
|---|---|
| Graphite (letter and text) | `#1F2428` |
| Accent blue (light background) | `#2F6FDB` |
| Accent blue (dark background) | `#5B9BFF` |
| Light text on dark background | `#F1F3F5` |
| Tagline (light / dark background) | `#5B636B` / `#AEB5BC` |

## Fonts
- Name: **JetBrains Mono Bold**
- Tagline: **Inter Regular**

Both are free (SIL Open Font License) and available on Google Fonts.

## Usage
- Keep a clear area around the logo of at least half the width of the "b".
- Below 24 px in height, use the symbol only. Below 48 px, use the simplified favicon (`favicon-light.svg`).
- Do not distort, rotate, or change the colors outside the versions above.

## Favicon on a web page

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon-180.png">
```

`favicon.svg` automatically switches to the light version when the browser is in dark mode.
