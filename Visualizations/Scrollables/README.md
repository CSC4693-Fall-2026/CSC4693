# Scrollable data visualizations

This Vite workspace contains scroll-driven data visualizations built with D3 and Scrollama. 

[`scrollable_map/`](scrollable_map/): **California's graduate earnings**.

## Run locally

From this directory:

```powershell
npm install
npm run prepare-data
npm run dev
```

Open the `scrollable_map/` link shown by Vite.

## Structure

- `scrollable_map/` — implemented four-step California earnings story.
- `scrollable_map/data/prepare_map_data.py` — produces browser-ready data in `data/derived/` and copies it into the Vite public assets.
- `scrollable_map/data/CaliforniaCollegeLoc.csv` — IPEDS-based California institution locations.
- `scrollable_pay_gap/` — documentation-only placeholder for the second story.

## Story and data

The statewide gap is explicitly a proof-of-concept comparison, not an estimate of faculty pay at each institution. Comparable faculty data is currently available only for Cal Poly, so the same Cal Poly benchmark is applied to every school. Hover details disclose the values used.

The preparation script reads `ca_collegescore.csv`, `calpoly_salary_data.csv`, `calpoly_major_medians.csv`, and `calpoly_scorecard.csv` from `Steel Thread/for_analysis/`. 

The map draws California from the bundled `us-atlas` TopoJSON dataset through `topojson-client` and has no runtime external-data dependency.
