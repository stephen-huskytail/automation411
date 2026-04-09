# Automation411 Website MVP

Initial production-ready static website implementation for Automation411.

## What is included

- Landing page with clear positioning and call-to-action flow
- Services and process sections for immediate sales use
- Contact form UX pattern with accessible status feedback
- Mobile-friendly responsive layout and lightweight animations
- No build tooling required for MVP delivery

## Local run

Use any static web server. Two quick options:

```bash
python3 -m http.server 8080
# open http://localhost:8080
```

Or:

```bash
npx serve .
```

## Build / deploy

This is a static site (`index.html`, `styles.css`, `script.js`), so there is no compile step.

Recommended go-live path:

1. Deploy on **Cloudflare Pages** or **Netlify** directly from the `main` branch.
2. Configure a custom domain (for example, `automation411.com`).
3. Add form handling integration (Netlify Forms, Formspree, or API endpoint) for real lead capture.
4. Add analytics (Plausible or GA4) and conversion event tracking.

## Next production hardening

- Connect the lead form to backend/email pipeline
- Add privacy policy + terms page
- Add favicon/social preview metadata
- Set up uptime checks and deployment notifications
