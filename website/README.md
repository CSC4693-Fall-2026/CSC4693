# Website

A small Vite + TypeScript site that embeds the [Role Distribution & Pay Per Campus](https://public.tableau.com/app/profile/sam.phan/viz/Week10-RoleDistPayPerCampus/Campus-Role?publish=yes) Tableau Public dashboard on the home page.

## Prerequisites

- Node.js 20.19+ or 22.12+ (check with `node -v`)

## Setup

```bash
cd website
npm install
npm run dev
```

Open the URL printed in the terminal (usually http://localhost:5173).

## Scripts

- `npm run dev` — start the local dev server with hot reload
- `npm run build` — type-check and build the production site into `dist/`
- `npm run preview` — serve the built `dist/` output locally

## Notes

- The Tableau viz is loaded at runtime from `public.tableau.com` (see the `<script>` tag in [index.html](index.html)) rather than bundled, per Tableau's recommendation for Tableau Public embeds.
- The embed URL is set in [src/main.ts](src/main.ts) as `VIZ_URL`. If the dashboard is republished to a new URL, update it there.
