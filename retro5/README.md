# PaperRank (essay-style dashboard)

1. Put this `retro/` folder inside the project folder, next to `clean/` and `interim/` (or set env var `DCV_ROOT` to the project folder).
2. `pip install -r requirements.txt`
3. `python app.py`, open http://127.0.0.1:8050

`config.py` (team, contributions, licence and terms), `institution_types.csv` (created on first run, edit labels), `assets/retro.css` (colours are the variables at the top), `charts.py`, `app.py`.
Fonts (Shrikhand, Fraunces, Jost) load from Google Fonts; offline you get fallback fonts.
Tabs: Front page (3D spinning scatter, ranking race, Sankey), Does it track? (animated scatter, gauges, correlation, robustness), Flows (2 Sankeys, treemap, sunburst), Institutions (radar, trajectories, bump chart, rank calendar), Landscape (violin, 3D surface, parallel coordinates), Gaps (lollipop, churn, violin), Behind the data (before/after, funnel, dumbbell, outliers, log), Credits.

Course checks built in (DA2402 lectures): dbc grid (Row and Col widths add up to 12), a Store for the shared selection, SQLite queries with parameters (`data.history`, `data.window_total`, used when `data/dcv_*.sqlite` exists), one highlight colour with grey (the Colour control), a "What it hides" line under each chart, and `python cbcheck.py` for the colour-blind simulation.
Beyond the lectures: Sankey, radar, gauge, 3D surface and bootstrap intervals (listed on the Credits page).
