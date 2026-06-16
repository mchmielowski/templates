# AI assistant guide

This is a **static HTML + CSS + JavaScript** website template — no build step, no
framework. Edits to `.html`/`.css` files take effect on refresh. Read this first.

## Where things live
- `css/styles.css` — the design: tokens (`:root`) + all component styles. Change colors/fonts/
  spacing here and they cascade everywhere.
- `css/components.css`, `css/normalize.css` — framework/reset, rarely edit.
- `js/main.js` — the animation engine. **DO NOT EDIT.**
- `js/*.min.js` — jQuery/GSAP libraries. Don't edit.
- `images/ fonts/ videos/` — assets.
- Pages (32): 401.html, 404.html, about/about-a.html, about/about-b.html, about/about-c.html, blog.html, career-detail.html, careers.html, checkout.html, contact.html, detail_blog.html, detail_careers.html, detail_category.html, detail_product.html …

## Critical rules
1. **Nav and footer are duplicated in EVERY page file** (no shared components). If you
   change navigation/logo/footer, make the SAME edit in all `.html` files or the site
   becomes inconsistent.
2. **Do not edit `js/main.js` or remove `data-w-id` / `w-*` attributes** — that's the
   animation/interaction engine (tabs, sliders, dropdowns, scroll reveals). Editing it
   breaks the motion.
3. **Keep the `<script>` tags at the bottom of each page** — they load the animations.

## Not wired up (intentional)
- Forms don't submit until you set a form `action` (e.g. Formspree).
- Listings (blog/case studies) are static HTML cards, not a live CMS.
- Content is sample copy; `og:image` is a placeholder — replace both.

## Customize design via tokens (in `css/styles.css` `:root`)
```css
--color-tokens-tone-strong: #0d4d4d;      /* primary text & buttons */
--color-tokens-background-base: #ffffff;   /* background */
--typography-font-heading-sans: "Your Font", sans-serif;
```
