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

- `scrollable_map/` — implemented scrollable story.
- `scrollable_map/data/prepare_map_data.py` — produces browser-ready data in `data/derived/` and copies it into the Vite public assets.
- `scrollable_map/data/CaliforniaCollegeLoc.csv` — locations of colleges for map
- `scrollable_pay_gap/` — place holder for other scrollable (if wanted to use)

## Story and data

The statewide gap is explicitly a proof-of-concept comparison, not an estimate of faculty pay at each institution. Faculty pay data is currently only available from Cal Poly so that is used for comparisons and visualizations.

The preparation script reads `ca_collegescore.csv`, `calpoly_salary_data.csv`, `calpoly_major_medians.csv`, and `calpoly_scorecard.csv` from `Steel Thread/for_analysis/`. 

The map draws California from the bundled `us-atlas` TopoJSON dataset through `topojson-client` and has no runtime external-data dependency.
